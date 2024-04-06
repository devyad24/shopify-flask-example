import logging
import uuid
import os
import json

from flask import Flask, redirect, request, render_template
from flask_sqlalchemy import SQLAlchemy


import helpers
from shopify_client import ShopifyStoreClient

from dotenv import load_dotenv

load_dotenv()
WEBHOOK_APP_UNINSTALL_URL = os.environ.get('WEBHOOK_APP_UNINSTALL_URL')
print('webhook', WEBHOOK_APP_UNINSTALL_URL)
WEBHOOK_APP_SHOP_DATA_REMOVAL = os.environ.get('WEBHOOK_APP_SHOP_DATA_REMOVAL')
print('webhook2',WEBHOOK_APP_SHOP_DATA_REMOVAL)


app = Flask(__name__)

#Configure DB
app.config["SQLALCHEMY_DATABASE_URI"] = 'postgresql://postgres:4211@localhost:5432/shop'

db = SQLAlchemy(app)


class shop(db.Model):
    ShopName = db.Column(db.VARCHAR, primary_key = True)
    Acccess_Token = db.Column(db.VARCHAR)

ACCESS_TOKEN = None
NONCE = None
#When online access mode is requested and the app is not already installed on a store, 
#the user installing the app must have access to all required scopes, or the installation fails.
ACCESS_MODE = []  # Defaults to offline access mode if left blank or omitted. https://shopify.dev/apps/auth/oauth/access-modes
#write_script_tags helps use execute js code on shopify storefront
SCOPES = ['write_script_tags']  # https://shopify.dev/docs/admin-api/access-scopes 

@app.route('/')
def index():
    shops = shop.query.all()
    print(shops)
    return 'Hello'
@app.route('/app_launched', methods=['GET'])
@helpers.verify_web_call
def app_launched():
    shop = request.args.get('shop')
    global ACCESS_TOKEN, NONCE

    print(f'Scopes: {SCOPES}')
    print(f'Access Mode: {ACCESS_MODE}')

    if ACCESS_TOKEN:
        return render_template('welcome.html', shop=shop)

    # The NONCE is a single-use random value we send to Shopify so we know the next call from Shopify is valid (see #app_installed)
    #   https://en.wikipedia.org/wiki/Cryptographic_nonce
    NONCE = uuid.uuid4().hex
    redirect_url = helpers.generate_install_redirect_url(shop=shop, scopes=SCOPES, nonce=NONCE, access_mode=ACCESS_MODE)
    return redirect(redirect_url, code=302)


@app.route('/app_installed', methods=['GET'])
@helpers.verify_web_call
def app_installed():
    state = request.args.get('state')
    global NONCE, ACCESS_TOKEN

    # Shopify passes our NONCE, created in #app_launched, as the `state` parameter, we need to ensure it matches!
    if state != NONCE:
        return "Invalid `state` received", 400
    NONCE = None

    # Ok, NONCE matches, we can get rid of it now (a nonce, by definition, should only be used once)
    # Using the `code` received from Shopify we can now generate an access token that is specific to the specified `shop` with the
    #   ACCESS_MODE and SCOPES we asked for in #app_installed
    shop_name = request.args.get('shop')
    code = request.args.get('code')
    ACCESS_TOKEN = ShopifyStoreClient.authenticate(shop=shop_name, code=code)

    existing_shop = shop.query.filter_by(ShopName=shop_name).first()

    if existing_shop is None:
        new_shop = shop(ShopName=shop_name, Acccess_Token=ACCESS_TOKEN)
        db.session.add(new_shop)
        db.session.commit()

    # We have an access token! Now let's register a webhook so Shopify will notify us if/when the app gets uninstalled
    # NOTE This webhook will call the #app_uninstalled function defined below
    shopify_client = ShopifyStoreClient(shop=shop_name, access_token=ACCESS_TOKEN)
    shopify_client.create_webook(address=WEBHOOK_APP_UNINSTALL_URL, topic="app/uninstalled")

    redirect_url = helpers.generate_post_install_redirect_url(shop=shop_name)
    return redirect(redirect_url, code=302)


@app.route('/app_uninstalled', methods=['POST'])
@helpers.verify_webhook_call
def app_uninstalled():
    # https://shopify.dev/docs/admin-api/rest/reference/events/webhook?api[version]=2020-04
    # Someone uninstalled your app, clean up anything you need to
    # NOTE the shop ACCESS_TOKEN is now void!
    global ACCESS_TOKEN
    ACCESS_TOKEN = None

    webhook_topic = request.headers.get('X-Shopify-Topic')
    webhook_payload = request.get_json()
    shop_name = webhook_payload["domain"]
    print(shop_name)
    
    # db.session.delete(shop_name)
    # db.session.commit()

    shop_to_delete = shop.query.filter_by(ShopName=shop_name).delete()
    db.session.commit()
    print(shop_to_delete)
    logging.error(msg={f"webhook call received {webhook_topic}:\n{json.dumps(webhook_payload, indent=4)}"})

    return "OK"


@app.route('/data_removal_request', methods=['POST'])
@helpers.verify_webhook_call
def data_removal_request():
    # https://shopify.dev/tutorials/add-gdpr-webhooks-to-your-app
    # Clear all personal information you may have stored about the specified shop
    webhook_topic = request.headers.get('X-Shopify-Topic')
    webhook_payload = request.get_json()
    shop = webhook_payload['shop_domain']
    print("--------------------------------------------------------------")
    print(shop)
    print("--------------------------------------------------------------")
    logging.error(msg={f"webhook call received {webhook_topic}:\n{json.dumps(webhook_payload, indent=4)}"})
    print("--------------------------------------------------------------")
    return "OK"


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
