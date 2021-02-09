import datetime
import sys
import logging
# import asyncio
from avgEmas import AvgEmas
import time
import multiprocessing
from flask import Flask
from flask import request, jsonify, Blueprint, abort

app = Flask(__name__)
catalog = Blueprint('lemo', __name__)
apikey = ''
secretkey = ''

@app.route("/signal")
def run():
    try:
        avgEmas = AvgEmas(apikey, secretkey, '1h', 0.01)
        horaAgora = datetime.datetime.now()
        print("Agora sao: ", horaAgora)
        sigs = avgEmas.run()
        print(sigs)
        return jsonify(sigs) 
        # pr1 = multiprocessing.Process(target=avgEmas.run)
        # pr1.start()
        #
        # tpl = (pr1, 0.01, '1h')
        # prcs.append(tpl)
        # return 0
        #pr1.join()
    except Exception as ex:
        print(ex)
        return []


@app.route("/hello")
def hello():
    return "Hello"

# def execBot():
if __name__ == "__main__":
    app.run(host= '0.0.0.0', port=5000)
