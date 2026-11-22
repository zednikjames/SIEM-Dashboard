import configparser
import os

from flask import Flask, request, jsonify


FOLDER_PATH = "C:\\Users\\james\\OneDrive\\Desktop\\SIEM Dashboard\\Forwarded-Logs\\"

config = configparser.ConfigParser()
config.read("collector.ini")

host = config.get("server", "host")
port = config.get("server", "port")
api_key = config.get("server", "api_key")

app = Flask(__name__)

@app.route("/api/collect", methods=['POST'])
def collect():
    data = request.form.to_dict()
    api_token = data.get('api_token')

    file = request.files.get('file')

    if api_token == api_key and file is not None and file.filename:
        print(f"Token matches: {api_token == api_key}")
        print(f"File received: {file}")
        print(f"Filename: {file.filename}")
                
        os.makedirs(FOLDER_PATH, exist_ok=True)
        file_path = os.path.join(FOLDER_PATH, file.filename)
        print(f"Full path: {file_path}")
        
        file.save(file_path)
        print(f"File saved successfully to: {file_path}")
        return jsonify(True)
    else:
        print(f"Check failed:")
        print(f"  Token match: {api_token == api_key}")
        print(f"  File is not None: {file is not None}")
        print(f"  File filename: {file.filename if file else 'No file'}")
    return jsonify(False)

if __name__ == "__main__":
    app.run(host, int(port))