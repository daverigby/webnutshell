from collections import namedtuple
import json

from flask import Flask, request, redirect, abort, render_template

from couchbase import Couchbase
from couchbase.exceptions import KeyExistsError, NotFoundError
from couchbase.views.iterator import RowProcessor
from couchbase.views.params import UNSPEC, Query


CustomerRow = namedtuple('CustomerRow', ['name', 'value', 'id', 'doc'])

class Node_Snapshot(object):
    def __init__(self, id, name, doc=None):
        self.id = id
        self.name = name
        self.customer = None
        self.doc = doc

    def __getattr__(self, name):
        if not self.doc:
            return ""
        return self.doc.get(name, "")


class Node_SnapshotListRowProcessor(object):
    """
    This is the row processor for listing all logs (with their customer IDs).
    """
    def handle_rows(self, rows, connection, include_docs):
        ret = []
        by_docids = {}

        for r in rows:
            b = Node_Snapshot(r['id'], r['key'])
            ret.append(b)
            by_docids[b.id] = b

        keys_to_fetch = [x.id for x in ret]
        docs = connection.get_multi(keys_to_fetch, quiet=True)

        for log_id, doc in docs.items():
            if not doc.success:
                ret.remove(log_id)
                continue

            log = by_docids[log_id]
            log.customer_id = doc.value['customer_id']

        return ret

DATABASE = 'nutshell'
HOST = 'localhost'
ENTRIES_PER_PAGE = 30



app = Flask(__name__, static_url_path='')
app.config.from_object(__name__)

def connect_db():
    return Couchbase.connect(
            bucket=app.config['DATABASE'],
            host=app.config['HOST'])


db = connect_db()

@app.route('/')
@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/logs')
def logs():
    rp = Node_SnapshotListRowProcessor()
    rows = db.query("node_snapshot", "by_name",
                    limit=ENTRIES_PER_PAGE,
                    row_processor=rp)

    return render_template('log/index.html', results=rows)

@app.route('/customers')
def customers():
    rp = RowProcessor(rowclass=CustomerRow)
    customer_rows = db.query("customer", "by_name",
                    row_processor=rp,
                    limit=ENTRIES_PER_PAGE)

    return render_template('customer/index.html', customers=customer_rows)


@app.route('/<otype>/delete/<id>')
def delete_object(otype, id):
    try:
        db.delete(id)
        return redirect('/welcome')

    except NotFoundError:
        return "No such {0} '{1}'".format(otype, id), 404

@app.route('/logs/show/<log_id>')
def show_log(log_id):
    doc = db.get(log_id, quiet=True)
    if not doc.success:
        return "No such log {0}".format(log_id), 404


    return render_template(
        'log/show.html',
        log=Node_Snapshot(log_id, doc.value['name'], doc.value))

@app.route('/customers/show/<customer>')
def show_customer(customer):
    doc = db.get(customer, quiet=True)
    if not doc.success:
        return "No such customer {0}".format(customer), 404

    obj = CustomerRow(name=doc.value['name'], value=None, id=customer, doc=doc.value)

    rp = Node_SnapshotListRowProcessor()
    q = Query()
    q.mapkey_single = customer
    q.limit = ENTRIES_PER_PAGE
    log_rows = db.query("node_snapshot", "by_customer",
                    row_processor=rp,
                    query=q,
                    include_docs=True)
    logs = []
    for log in log_rows:
        logs.append({'id' : log.id,
                    'name' : log.name})

    rp = RowProcessor(rowclass=CustomerRow)
    cluster_rows = db.query("cluster", "by_customer",
                    row_processor=rp,
                    query=q,
                    include_docs=True)
    clusters = []
    for cluster in cluster_rows:
        clusters.append({'id' : cluster.id,
                    'name' : cluster.name})

    return render_template('/customer/show.html', customer=obj, logs=logs, clusters=clusters)

#@app.route('/logs/edit/<log>')
#def edit_beer_display(beer):
#    bdoc = db.get(beer, quiet=True)
#    if not bdoc.success:
#        return "No Such Beer", 404
#
#    return render_template('beer/edit.html',
#                           beer=Beer(beer, bdoc.value['name'], bdoc.value),
#                           is_create=False)

@app.route('/beers/create')
def create_beer_display():
    return render_template('beer/edit.html', beer=Beer('', ''), is_create=True)


def normalize_log_fields(form):
    doc = {}
    for k, v in form.items():
        name_base, fieldname = k.split('_', 1)
        if name_base != 'log':
            continue

        doc[fieldname] = v

    if not 'name' in doc or not doc['name']:
        return (None, ("Must have name", 400))

    if not 'customer_id' in doc or not doc['customer_id']:
        return (None, ("Must have customer ID", 400))

    if not db.get(doc['customer_id'], quiet=True).success:
        return (None,
                ("Customer ID {0} not found".format(doc['customer_id']), 400))

    return doc, None


#@app.route('/beers/create', methods=['POST'])
#def create_beer_submit():
#    doc, err = normalize_beer_fields(request.form)
#    if not doc:
#        return err
#
#    id = '{0}-{1}'.format(doc['brewery_id'],
#                          doc['name'].replace(' ', '_').lower())
#    try:
#        db.add(id, doc)
#        return redirect('/beers/show/' + id)
#
#    except KeyExistsError:
#        return "Beer already exists!", 400

#@app.route('/beers/edit/<beer>', methods=['POST'])
#def edit_beer_submit(beer):
#    doc, err = normalize_beer_fields(request.form)
#
#    if not doc:
#        return err
#
#    db.set(beer, doc)
#    return redirect('/beers/show/' + beer)


def return_search_json(ret):
    response = app.make_response(json.dumps(ret))
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/logs/search')
def log_search():
    value = request.args.get('value')
    q = Query()
    q.mapkey_range = [value, value + Query.STRING_RANGE_END]
    q.limit = ENTRIES_PER_PAGE

    ret = []

    rp = Node_SnapshotListRowProcessor()
    res = db.query("node_snapshot", "by_name",
                   row_processor=rp,
                   query=q,
                   include_docs=True)

    for log in res:
        ret.append({'id' : log.id,
                    'name' : log.name,
                    'customer' : log.customer_id})

    return return_search_json(ret)

@app.route('/customers/search')
def customer_search():
    value = request.args.get('value')
    q = Query()
    q.mapkey_range = [value, value + Query.STRING_RANGE_END]
    q.limit = ENTRIES_PER_PAGE

    ret = []

    rp = RowProcessor(rowclass=CustomerRow)
    res = db.query("customer", "by_name",
                   row_processor=rp,
                   query=q,
                   include_docs=True)
    for customer in res:
        print customer
        ret.append({'id' : customer.id,
                    'name' : customer.name})

    return return_search_json(ret)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
