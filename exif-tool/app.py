from flask import Flask, render_template, request, flash, redirect, url_for
import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from geopy.geocoders import Nominatim
import base64
import io

app = Flask(__name__)
app.secret_key = "exif_secret_key"

geolocator = Nominatim(user_agent="exif_extractor_app")

def get_decimal_from_dms(dms, ref):
    try:
        degrees = dms[0]
        minutes = dms[1] / 60.0
        seconds = dms[2] / 3600.0
        if ref in ['S', 'W']:
            degrees = -degrees
            minutes = -minutes
            seconds = -seconds
        return float(degrees + minutes + seconds)
    except:
        return 0.0

def get_exif_data(image_file):
    try:
        image = Image.open(image_file)
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
        # Save stream to memory for multiple uses
        img_stream = io.BytesIO(file.read())
        
        # Get EXIF
        img_stream.seek(0)
        exif = get_exif_data(img_stream)
        metadata = extract_metadata(exif)
        
        # Convert image to base64 for preview (avoids saving to disk)
        img_stream.seek(0)
        encoded_img = base64.b64encode(img_stream.read()).decode('utf-8')
        image_url = f"data:image/jpeg;base64,{encoded_img}"
        
        return render_template('results.html', metadata=metadata, image_url=image_url)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
