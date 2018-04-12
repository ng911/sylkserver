import traceback
from flask import Blueprint, jsonify
from flask_cors import CORS, cross_origin
from sylk.applications import ApplicationLogger
from sylk.db.schema import User
from sylk.data.calltaker import CalltakerData
from utils import get_argument

psap = Blueprint('psap', __name__,
                        template_folder='templates')

CORS(psap)
log = ApplicationLogger(__package__)

'''
Note - for now we ignore the psap_id
'''
@psap.route('/', methods=['GET'])
def sops():
    response = {
        'success' : True,
        'sops' : {}
    }

    return jsonify(response)
