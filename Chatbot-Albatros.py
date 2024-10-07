import requests
import json
import gradio as gr
import fitz
import logging
import base64
from flask import Flask, request, jsonify

# Configuration du logger
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Remplacez par votre clé API
OPENROUTER_API_KEY = "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"
YOUR_SITE_URL = "votre-site.com"  # Remplacez par votre URL
YOUR_APP_NAME = "MonChatbot"

def extract_text_from_pdf(pdf_file):
    doc = fitz.open(pdf_file)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def chatbot_response(message, history, pdf_text=None, image_path=None):
    messages = [{"role": "system", "content": "Vous êtes un assistant IA utile et amical, capable d'analyser des images et du texte."}]
    
    if pdf_text:
        messages.append({"role": "system", "content": f"Le contenu du PDF est : {pdf_text}"})
    
    for human, assistant in history:
        messages.append({"role": "user", "content": human})
        if assistant is not None:
            messages.append({"role": "assistant", "content": assistant})
    
    message_content = message
    if image_path:
        encoded_image = encode_image(image_path)
        message_content = [
            {"type": "text", "text": message},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
        ]
    
    messages.append({"role": "user", "content": message_content})
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": f"{YOUR_SITE_URL}",
                "X-Title": f"{YOUR_APP_NAME}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "mistralai/pixtral-12b:free",
                "messages": messages
            })
        )
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            return f"Erreur {response.status_code}: {response.text}"
    except Exception as e:
        logger.error(f"Erreur lors de l'appel API: {str(e)}")
        return f"Erreur: {str(e)}"

@app.route('/api/chatbot', methods=['POST'])
def api_chatbot():
    try:
        message = request.form.get('message')
        pdf_file = request.files.get('pdf')
        pdf_text = extract_text_from_pdf(pdf_file) if pdf_file else None
        history = request.json.get('history', [])
        
        # Appel du chatbot pour obtenir la réponse
        response = chatbot_response(message, history, pdf_text)
        
        return jsonify({'response': response})
    
    except Exception as e:
        logger.error(f"Erreur dans l'API: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Créer l'interface Gradio pour une utilisation normale
# Définir la fonction user
def user(user_message, history, pdf_text, image):
    # Retourne un message vide et met à jour l'historique de la conversation
    return "", history + [[user_message, None]], pdf_text, image

def bot(history, pdf_text, image):
    if history:
        # Le dernier message utilisateur est passé à la fonction chatbot_response
        bot_message = chatbot_response(history[-1][0], history[:-1], pdf_text, image)
        history[-1][1] = bot_message  # Mettre à jour l'historique avec la réponse du bot
        return history
    return []

def clear_chat():
    return [], None, None

# Interface Gradio
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    chatbot = gr.Chatbot(label="Historique de la conversation")
    msg = gr.Textbox(label="Votre message", placeholder="Tapez votre message ici...")
    pdf_upload = gr.File(label="Téléchargez un fichier PDF", file_types=[".pdf"])
    image_upload = gr.Image(type="filepath", label="Téléchargez une image")
    clear = gr.Button("Effacer la conversation")
    pdf_text = gr.State()
    
    # Lorsqu'un fichier PDF est uploadé, extrait le texte du PDF
    pdf_upload.change(lambda file: extract_text_from_pdf(file), pdf_upload, pdf_text)
    
    # Lorsqu'un message est envoyé, met à jour le chatbot
    msg.submit(user, [msg, chatbot, pdf_text, image_upload], [msg, chatbot, pdf_text, image_upload], queue=False).then(
        bot, [chatbot, pdf_text, image_upload], chatbot
    )
    
    # Efface la conversation
    clear.click(clear_chat, None, [chatbot, pdf_text, image_upload], queue=False)

demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 5000)))

# Lancer l'application Flask pour la gestion des API
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Utilise le port fourni par Heroku
    app.run(host="0.0.0.0", port=port)        # Assure-toi que Flask/Gradio écoute sur 0.0.0.0