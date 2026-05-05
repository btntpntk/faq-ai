import os

import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()

voice_name = "th-TH-PremwadeeNeural"

def speak_thai_text(text: str, output_file: str | None = None):
    speech_config = speechsdk.SpeechConfig(
        subscription=os.environ["AZURE_SPEECH_KEY"],
        region=os.environ["AZURE_SERVICE_REGION"],
    )

    if output_file:
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
    else:
        audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    # Escape XML characters for SSML
    safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # --- 2. Construct the SSML String ---
    # SSML allows for precise control over the Thai voice behavior.
    ssml_content = f"""
    <speak version='1.0'
        xmlns='http://www.w3.org/2001/10/synthesis'
        xmlns:mstts='http://www.w3.org/2001/mstts'
        xml:lang='th-TH'>
        <voice name='{voice_name}'>
            <mstts:express-as style='customerservice' styledegree='1.5'>
                <prosody rate='0.9' pitch='medium'>
                    {safe_text}
                </prosody>
            </mstts:express-as>
        </voice>
    </speak>
    """

    # --- 3. Execute Synthesis ---
    # print("Synthesizing speech from SSML...")
    result = speech_synthesizer.speak_ssml_async(ssml_content).get()

    # --- 4. Error Handling & Confirmation ---
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        pass
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"Speech synthesis canceled: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {cancellation_details.error_details}")

if __name__ == "__main__":
    speak_thai_text("สวัสดีค่ะ บริษัทหลักทรัพย์ทรีนีตี้ จำกัด ยินดีให้บริการ")