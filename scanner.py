import face_recognition
from PIL import Image
import os
import numpy as np

def process_and_encode_livestock(image_path):
    """
    Combines image quality check with biometric face/muzzle recognition.
    """
    try:
        # 1. QUALITY CHECK (Your original logic)
        with Image.open(image_path) as img:
            width, height = img.size
            if width < 500 or height < 500:
                return "Error: Photo too blurry for Suguta Valley standards"

        # 2. BIOMETRIC EXTRACTION
        # Load the image for the AI
        image = face_recognition.load_image_file(image_path)
        
        # Find all face/muzzle locations in the image
        face_locations = face_recognition.face_locations(image)
        
        if not face_locations:
            return "Error: No animal face or muzzle detected. Please reposition."

        # Generate the 128-dimension encoding (the 'Identity')
        encodings = face_recognition.face_encodings(image, face_locations)
        
        if encodings:
            # Return the encoding so it can be saved to database.py
            return {"status": "Success", "encoding": encodings[0]}
        else:
            return "Error: Failed to capture unique muzzle pattern."

    except Exception as e:
        return f"Error: Not a valid image file. {str(e)}"

def verify_match(stored_encoding, current_encoding, threshold=0.5):
    """
    Compares a scanned animal against a 'Stolen' record.
    Threshold 0.5 is strict; 0.6 is more lenient.
    """
    results = face_recognition.compare_faces([stored_encoding], current_encoding, tolerance=threshold)
    return results[0]