import requests
import json
import gradio as gr
import fitz
import logging
import base64
from flask import Flask, request, jsonify
import io
import os
from PyPDF2 import PdfReader

# Configuration du logger
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Remplacez par votre clé API
OPENROUTER_API_KEY = "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"
YOUR_SITE_URL = "votre-site.com"
YOUR_APP_NAME = "MonChatbot"
MAKE_WEBHOOK_URL = "https://hook.eu2.make.com/yqq8mqiruhwz5j96gqyanpscm3stbydt"  # Webhook Make pour Google Docs

def extract_text_from_pdf(pdf_file):
    doc = fitz.open(pdf_file)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def chatbot_response(message, pdf_text=None):
    messages = [{"role": "system", "content": "Vous êtes un assistant IA RH qui analyse des CV de manière complete en analysant les compétences. Vous retournez strictement que des compétences ou mail sans faire de commentaires et séparé de (;) "}]
    
    if pdf_text:
        messages.append({"role": "system", "content": f"Le contenu du PDF est : {pdf_text}"})
    
    messages.append({"role": "user", "content": message})
    
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
                "model": "meta-llama/llama-3.2-11b-vision-instruct:free",
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
        # Message prédéfini pour le chatbot avec les instructions de formatage du mail et des compétences
        message = """Je suis un chatbot spécialisé en analyse de CV. Votre tâche est d’analyser le CV fourni et d'identifier les 3 compétences principales qui s’y trouvent. Voici la liste de compétences que vous devez utiliser strictement pour votre analyse (vous devez reprendre exactement la même orthographe et formulation) :

[Gestion de projet ; Analyse de données ; Programmation en Python ; Conception de circuits électroniques ; Modélisation 3D (CATIA, SolidWorks) ; Connaissance en C/C++ ; Gestion des systèmes embarqués ; Automatisation des processus ; Conception mécanique ; Simulation (MATLAB, Simulink) ; Analyse de la fiabilité (FMEA) ; Communication technique ; Résolution de problèmes complexes ; Connaissances en Intelligence Artificielle ; Systèmes de contrôle ; Programmation en Java ; Développement logiciel (Scrum, Agile) ; Design des expériences utilisateur (UX/UI) ; Conception et analyse des matériaux ; Gestion de la chaîne d’approvisionnement ; Conception de bases de données (SQL, NoSQL) ; Automatisation industrielle (PLC, SCADA) ; Connaissance en sécurité informatique ; Méthodes d’optimisation ; Analyse des vibrations et acoustique ; Réseaux et télécommunications ; Programmation web (HTML, CSS, JavaScript) ; Systèmes de vision par ordinateur ; Analyse de systèmes thermiques ; Travail en équipe et collaboration interdisciplinaire].

Contraintes importantes :
1. Vous devez obligatoirement choisir les 3 compétences parmi la liste fournie même si la compétences n'est pas forcément entierement compatible.
2. Vous devez utiliser exactement le même nom de compétence de la liste, sans modification,sans ajout, même si la compétence ne correspond pas à 100%.
3. Formatez la réponse comme suit : email@example.com;compétence1;compétence2;compétence3.
4. Ne pas ajouter de commentaire, de contexte ou de texte explicatif. Répondez uniquement dans le format demandé.

Exemple de réponse correcte :
mail@mail.com;Programmation en Python;Analyse de données;Communication technique"""
        
        # Récupérer le fichier PDF uploadé
        pdf_file = request.files.get('pdf')
        if not pdf_file:
            return jsonify({'error': 'Aucun fichier PDF reçu.'}), 400

        # Lire le contenu du PDF avec PyMuPDF (fitz)
        pdf_data = pdf_file.read()
        pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
        pdf_text = ""
        for page in pdf_doc:
            pdf_text += page.get_text()

        if not pdf_text:
            return jsonify({'error': 'Impossible d\'extraire le texte du PDF.'}), 500

        # Utiliser le texte extrait pour interagir avec le chatbot et récupérer la réponse
        chatbot_reply = chatbot_response(message, pdf_text=pdf_text)
        print("Chatbot reply:", chatbot_reply)  # Log pour vérifier la réponse du chatbot

        # Diviser la réponse en éléments séparés par des points-virgules
        elements = [elem.strip() for elem in chatbot_reply.split(';') if elem.strip()]
        print("Elements:", elements)  # Log pour vérifier les éléments extraits

        # Extraire le mail et les compétences
        mail = elements[0] if len(elements) > 0 else ""
        competences = elements[1:4]  # Les 3 compétences suivantes
        print("Mail:", mail)
        print("Competences:", competences)

        # Préparer les compétences pour le webhook de Make
        make_payload = {
            "mail": mail,
            "competence_1": competences[0] if len(competences) > 0 else "",
            "competence_2": competences[1] if len(competences) > 1 else "",
            "competence_3": competences[2] if len(competences) > 2 else ""
        }

        # Envoyer les données à Make
        make_response = requests.post(MAKE_WEBHOOK_URL, json=make_payload)
        if make_response.status_code != 200:
            return jsonify({'error': f"Échec de l'envoi à Make: {make_response.status_code} - {make_response.text}"}), 500

        return jsonify({'message': 'Compétences extraites et envoyées à Make pour Webflow', 'mail': mail, 'competences': competences})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
