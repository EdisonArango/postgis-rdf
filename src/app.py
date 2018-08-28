# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import math
import psycopg2

from flask import Flask, render_template, make_response, request
from psycopg2.extras import RealDictCursor
from rdflib import URIRef, Graph, Literal, Namespace
from rdflib.namespace import RDF, FOAF

templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=templates_dir)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, 'cache')

DB_HOST = 'db'  # Docker db host
DB_USER = 'geo'
DB_PASSWORD = 'geo'
DB_NAME = 'geo24'


TABLES = {
    'ecuador_provincial': {
        'id_column': 'dpa_provin',
        'name_column': 'dpa_despro'
    },
    'ecuador_cantonal': {
        'id_column': 'dpa_canton',
        'name_column': 'dpa_descan'
    },
    'ecuador_parroquial': {
        'id_column': 'dpa_parroq',
        'name_column': 'dpa_despar'
    }
}

URI_FORMAT = '{url_root}{table}/{id}.rdf'

def get_provincia(table, id):
    conn = psycopg2.connect('dbname={0} user={1} password={2} host={3}'.format(DB_NAME, DB_USER, DB_PASSWORD, DB_HOST))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    id_column = TABLES[table]['id_column']
    GN = Namespace('http://www.geonames.org/ontology#')
    g = Graph()
    if table == 'ecuador_provincial':
        query = "SELECT dpa_provin, dpa_despro, area_km2 FROM {table} where {id_column}='{id}'".format(table=table, id_column=id_column, id=id)
    elif table == 'ecuador_cantonal':
        query = "SELECT dpa_provin, dpa_despro, dpa_canton, dpa_descan FROM {table} where {id_column}='{id}'".format(table=table, id_column=id_column, id=id)
    elif table == 'ecuador_parroquial':
        query = "SELECT dpa_provin, dpa_despro, dpa_canton, dpa_descan, dpa_parroq, dpa_despar FROM {table} where {id_column}='{id}'".format(table=table, id_column=id_column, id=id)
    cur.execute(query)
    row = cur.fetchone()
    if table == 'ecuador_provincial':
        provincia = URIRef(URI_FORMAT.format(url_root=request.url_root, table=table, id=id))
        g.add((provincia, GN.name, Literal(row['dpa_despro'])))
        g.add((provincia, GN.area, Literal(row['area_km2'])))
    elif table == 'ecuador_cantonal':
        canton = URIRef(URI_FORMAT.format(url_root=request.url_root, table=table, id=id))
        provincia = URIRef(URI_FORMAT.format(url_root=request.url_root, table='ecuador_provincial', id=row['dpa_provin']))
        g.add((canton, GN.name, Literal(row['dpa_descan'])))
        g.add((canton, GN.parentADM1, provincia))
    elif table == 'ecuador_parroquial':
        parroquia = URIRef(URI_FORMAT.format(url_root=request.url_root, table=table, id=id))
        canton = URIRef(URI_FORMAT.format(url_root=request.url_root, table='ecuador_cantonal', id=row['dpa_canton']))
        provincia = URIRef(URI_FORMAT.format(url_root=request.url_root, table='ecuador_provincial', id=row['dpa_provin']))
        g.add((parroquia, GN.name, Literal(row['dpa_despar'])))
        g.add((parroquia, GN.parentADM1, canton))
        g.add((parroquia, GN.parentADM2, provincia))
    return g.serialize(format='xml')


def get_table_ref(table_name, table_info):
    ref = []
    conn = psycopg2.connect('dbname={0} user={1} password={2} host={3}'.format(DB_NAME, DB_USER, DB_PASSWORD, DB_HOST))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    query = "SELECT {id_column}, {name_column} FROM {table}".format(table=table_name, id_column=table_info['id_column'], name_column=table_info['name_column'])
    cur.execute(query)
    for el in cur:
        name = el[table_info['name_column']].decode('utf8')
        uri = URI_FORMAT.format(url_root=request.url_root, table=table_name, id=el[table_info['id_column']])
        ref.append({'name': name, 'uri': uri})
    return ref


def get_tables_refs():
    refs = []
    for name, value in TABLES.items():
        ref = {'name': name, 'values': get_table_ref(name, value)}
        refs.append(ref)
    return refs


@app.route('/')
def index():
    tables_refs = get_tables_refs()
    response = make_response(render_template('index.html', tables_refs=tables_refs))
    response.headers['Accept'] = '*/*'
    return response



@app.route('/*.rdf')
@app.route('/<string:table>.rdf')
@app.route('/<string:table>/<string:id>.rdf')
def rdf(table='ecuador_provincial', id=1):
    tile = get_provincia(table, id)
    response = make_response(tile)
    response.headers['Content-Type'] = "text/xml"
    return response


if __name__ == "__main__":
    if 'SERVER' in os.environ:
        app.run(host="0.0.0.0", port=80)
    else:
        app.run(host="0.0.0.0", port=5000)
