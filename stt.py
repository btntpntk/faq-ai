import os

import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()

SPEECH_KEY = os.environ["AZURE_SPEECH_KEY"]
SERVICE_REGION = os.environ["AZURE_SERVICE_REGION"]


def listen_thai() -> str:
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SERVICE_REGION)
    speech_config.speech_recognition_language = "th-TH"

    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)
    print("กำลังฟัง... (พูดได้เลย)")
    result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print(f"ได้ยิน: {result.text}")
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("ไม่ได้ยินเสียง")
    elif result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        print(f"ยกเลิก: {details.reason}")
        if details.reason == speechsdk.CancellationReason.Error:
            print(f"Error: {details.error_details}")
    return ""


if __name__ == "__main__":
    text = listen_thai()
    if text:
        print(f"ข้อความ: {text}")
