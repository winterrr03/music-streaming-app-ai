from flask import Flask, request, jsonify
import os
import numpy as np
from astrapy import DataAPIClient
from getEmbeds import generate_embedding
from flask_cors import CORS
import httpx

app = Flask(__name__)
CORS(app)
client = DataAPIClient(os.environ["ASTRA_DB_APPLICATION_TOKEN"])
database = client.get_database(os.environ["ASTRA_DB_API_ENDPOINT"])
collection = database.get_collection(os.environ["ASTRA_DB_COLLECTION"])
url = os.environ['BACKEND_URL']

@app.route('/', methods=['GET'])
def hello():
    return "Hello World!"

# @app.route('/songs', methods=['GET'])
# def output_songs():
#     try:
#         songs = collection.find()
#         song_list = [{'track': song['track'], 'artist': song['artist']} for song in songs]

#         response = jsonify(song_list)
#         response.headers.add('Access-Control-Allow-Origin', '*')
#         return response
#     except Exception as e:
#         return jsonify({"error retrieving songs from Astra": str(e)}), 500


@app.route('/recognize', methods=['POST'])
async def upload():
    try:
        file = request.files['audioFile']
        temp_dir = '/tmp'

        # Ensure the file path exists
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        temp_audio_path = os.path.join(temp_dir, file.filename)
        file.save(temp_audio_path) # Save the uploaded mp3 audio to the temp directory

        emb = generate_embedding(temp_audio_path)
        # emb_str = np.array2string(emb, separator=',', formatter={'float_kind':lambda x: "%.20f" % x}).replace(' ', '')
        
        # print("vector:", emb_str) # Debugging statement to see vector output
        
        # vector similiarity search
        results = collection.find(
        sort={"$vector": emb},
        limit=5)

        tracks = []
        async with httpx.AsyncClient() as client:
            for doc in results:
                track_id = doc['track_id']

                response = await client.get(f'{url}/tracks/{track_id}')
                
                if response.status_code == 200:
                    track_details = response.json()
                    tracks.append(track_details['result'])

        os.remove(temp_audio_path)

        response = jsonify({
            'message': 'Recognize song success',
            'result': tracks
        })
        response.headers.add('Access-Control-Allow-Origin', '*')

        return response
    except Exception as e:
            return jsonify({"error uploading audio": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
    # port=8080 for google cloud run