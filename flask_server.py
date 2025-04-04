from flask import Flask, jsonify, send_from_directory,render_template, request
import datetime
import os
import json
import webbrowser


DATA_FOLDER = "JSON_DATA"
NUM_POSTS_PER_LOAD = 5
files = sorted(os.listdir(DATA_FOLDER))
app = Flask(__name__)

@app.route('/')
def home():
    return send_from_directory('.', 'filltered_li.html')

@app.route('/load_data', methods=['POST'])
def load_data():
    print(files)
    file_index = int(request.json.get('file_index', -1))
    elem_index = int(request.json.get('elem_index', 0))
    posts_to_load = NUM_POSTS_PER_LOAD
    print(file_index)
    while file_index < len(files) and file_index != -1:
        file_path = os.path.join(DATA_FOLDER, files[file_index])
        with open(file_path) as f:
            data = json.load(f)

        return jsonify({'data': data, 'next': file_index + 1 if file_index + 1 < len(files) else -1})

    return jsonify({'data': [], 'next': -1})

if __name__ == '__main__':
    app.run(port=5000, debug=False)
    webbrowser.open_new_tab("http://127.0.0.1:5000")
