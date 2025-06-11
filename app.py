from flask import Flask, request, jsonify
import joblib
import pandas as pd
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import tensorflow as tf
import io
from PIL import Image
import textwrap
import json

with open("disease_mapping.json", "r") as f:
    disease_mapping = json.load(f)

# Inisialisasi Flask app
app = Flask(__name__)

# Load model tabular (misalnya model penyakit dari data fitur tabular)
model_tabular = joblib.load('best_model.pkl')
label_encoders = joblib.load('label_encoders.pkl')
label_encoder = label_encoders['Disease_Prediction']

# Load model CNN (untuk prediksi gambar)
model_cnn = load_model('model.h5')
class_labels_cnn = ['Flea_Allergy', 'Health', 'Ringworm', 'Scabies']

# Treatment suggestion
treatment_suggestions = {
    'Health': "The cat's skin appears healthy and free from skin disease symptoms. To maintain this health, ensure your cat stays in a clean environment free from parasites like fleas and mites. Provide high-nutrition food containing omega-3 and omega-6 to maintain skin and fur health. Bathe your cat regularly (about 1-2 times per month) with gentle cat-specific shampoo. Perform grooming to prevent matted fur and check for early signs of disease. Don't forget to schedule regular check-ups with a veterinarian at least once every 6 months.",
    'Flea_Allergy': "The cat shows symptoms of flea bite allergy, which typically includes severe itching, localized hair loss, and wounds from scratching. The first step is to immediately provide antiparasitic treatment such as spot-on or oral medication recommended by a veterinarian. Bathe the cat with flea-specific cat shampoo, and avoid using human products as they can be harmful. Clean all areas where the cat frequently stays—including beds, carpets, and furniture—as fleas can also nest there. Use a vacuum cleaner regularly and consider spraying flea treatment in the surrounding environment. If the condition doesn't improve within a few days, immediately consult a veterinarian for further treatment.",
    'Ringworm': "Ringworm or dermatophytosis is a highly contagious fungal infection, both to other cats, animals, and humans. Signs include circular hair loss, reddened skin, and scaling. Treatment begins with isolating the cat from other pets to prevent spread. Apply antifungal ointment such as miconazole or ketoconazole as prescribed by a veterinarian. Bathe the cat regularly with antifungal shampoo. All items that have been touched by the cat must be cleaned and disinfected, including bedding and toys. Oral medication may be needed in severe cases. Since fungal infections can last a long time, remain disciplined in treatment and continue veterinary check-ups until the cat is completely cured.",
    'Scabies': "Scabies in cats is caused by Sarcoptes or Notoedres mite infestation and is highly contagious. Symptoms include extreme itching, thickened and scaly skin, wounds from scratching, and may be accompanied by secondary infections. Treatment begins by taking the cat to a veterinarian for a definitive diagnosis (sometimes through skin scraping). The doctor will provide medication such as ivermectin, selamectin, or milbemycin. Bathe the cat with special antiparasitic shampoo and treat infected skin to prevent open wounds. Isolate the cat during treatment to prevent transmission to other animals or humans. The environment must also be intensively cleaned, and treatment must be continued until the mites are completely gone."
}

# Endpoint predict untuk data tabular
@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    input_data = data['data']
    df_input = pd.DataFrame([input_data])

    prediction = model_tabular.predict(df_input)
    prediction_proba = model_tabular.predict_proba(df_input)

    predicted_index = prediction[0]
    confidence = np.max(prediction_proba[0]) * 100
    predicted_label = label_encoder.inverse_transform([predicted_index])[0]  # string

    # Gunakan predicted_label sebagai key lookup
    result = disease_mapping.get(predicted_label, {
        "description": "No description available.",
        "treatment": "Please consult a vet.",
    })

    return jsonify({
        "prediction": predicted_label,
        "confidence": f"{confidence:.2f}%",
        "description": result["description"],
        "treatment": result["treatment"]
    })

# Endpoint predict untuk gambar
@app.route('/predict-image', methods=['POST'])
def predict_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # Load and preprocess image, force convert to RGB
        img = Image.open(io.BytesIO(file.read())).convert('RGB')
        img = img.resize((150, 150))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = img_array / 255.0

        # Predict
        prediction = model_cnn.predict(img_array)
        predicted_class = np.argmax(prediction, axis=1)[0]
        confidence = float(np.max(prediction[0]) * 100)
        predicted_label = class_labels_cnn[predicted_class]

        # Wrap treatment suggestion
        wrapped_text = textwrap.fill(treatment_suggestions[predicted_label], width=100)

        # Return response
        return jsonify({
            'prediction': predicted_label,
            'confidence': f"{confidence:.2f}%",
            'treatment_suggestion': wrapped_text
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({'error': str(e)}), 500

# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)

