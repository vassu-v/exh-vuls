from flask import Flask, render_template, request, flash, redirect, url_for
import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from geopy.geocoders import Nominatim
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = "exif_secret_key"
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

geolocator = Nominatim(user_agent="exif_extractor_app")

def get_decimal_from_dms(dms, ref):
    degrees = dms[0]
    minutes = dms[1] / 60.0
    seconds = dms[2] / 3600.0
    if ref in ['S', 'W']:
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds
    return degrees + minutes + seconds

def get_exif_data(image_path):
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if not exif_data:
            return None

        data = {}
        for tag, value in exif_data.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                gps_data = {}
                for t in value:
                    sub_decoded = GPSTAGS.get(t, t)
                    gps_data[sub_decoded] = value[t]
                data[decoded] = gps_data
            else:
                data[decoded] = value
        return data
    except Exception as e:
        print(f"Error reading EXIF: {e}")
        return None

def extract_metadata(exif):
    if not exif:
        return None

    metadata = {
        'lat': None,
        'lng': None,
        'address': "N/A",
        'date': exif.get('DateTimeOriginal', 'N/A'),
        'model': exif.get('Model', 'N/A'),
        'make': exif.get('Make', 'N/A')
    }

    if 'GPSInfo' in exif:
        gps = exif['GPSInfo']
        try:
            lat = get_decimal_from_dms(gps['GPSLatitude'], gps['GPSLatitudeRef'])
            lng = get_decimal_from_dms(gps['GPSLongitude'], gps['GPSLongitudeRef'])
            metadata['lat'] = lat
            metadata['lng'] = lng
            
            # Reverse Geocode
            location = geolocator.reverse(f"{lat}, {lng}", language='en')
            if location:
                metadata['address'] = location.address
        except Exception as e:
            print(f"GPS processing error: {e}")

    return metadata

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file:
        filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        exif = get_exif_data(filepath)
        metadata = extract_metadata(exif)
        
        return render_template('results.html', metadata=metadata, image_url=url_for('static', filename=f'uploads/{filename}'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
