from flask import Flask, jsonify, send_from_directory,render_template, request
import datetime
import os
import json
import webbrowser
import yaml


with open('config.yaml') as config_file:
    config = yaml.safe_load(config_file)

DATA_FOLDER = "JSON_DATA"
NUM_POSTS_PER_LOAD = config['posts_to_load']
PORT = config['PORT']
files = sorted(os.listdir(DATA_FOLDER))
app = Flask(__name__)

@app.route('/')
def home():
    return send_from_directory('.', 'filltered_li.html')

@app.route('/load_data', methods=['POST'])
def load_data():
    file_index = int(request.json.get('file_index', -1))
    elem_index = int(request.json.get('elem_index', 0))

    posts_left_to_load = NUM_POSTS_PER_LOAD
    out = []
    while file_index < len(files) and file_index != -1:
        file_path = os.path.join(DATA_FOLDER, files[-file_index-1])
        if not file_path.endswith(".json"):
            file_index+=1
            continue

        with open(file_path) as f:
            data = json.load(f)
        
        if elem_index + posts_left_to_load <= len(data):
            out+=data[elem_index:elem_index+posts_left_to_load]
            elem_index+=posts_left_to_load
        else:
            out+=data[elem_index:]
            if file_index + 1 < len(files):
                posts_left_to_load-= len(data[elem_index:])
                elem_index = 0
                file_index+=1
                continue
            else:
                file_index = -1
        
        return jsonify({'data': out, 'next': file_index, 'elem_index': elem_index})

    return jsonify({'data': [], 'next': -1, 'elem_index':-1})

if __name__ == '__main__':
    webbrowser.open_new_tab("http://127.0.0.1:5000")
    app.run(port=PORT, debug=False)
