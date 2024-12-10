# WhatsApp Utilities

This project is a Python & Go project that uses the WhatsApp Business Platform Cloud API and a series of online AI tools to provide you with several utilities under a WhatsApp contact. See more under [Features](#features)

This project is hosted in the DigitalOcean Functions free tier. Get a $200 credit for 60 days by clicking on the badge below.

[![DigitalOcean Referral Badge](https://web-platforms.sfo2.cdn.digitaloceanspaces.com/WWW/Badge%201.svg)](https://www.digitalocean.com/?refcode=d1b30a7a0c5b&utm_campaign=Referral_Invite&utm_medium=Referral_Program&utm_source=badge)

## Features

- Voicenote Transcriptor: Just send or forward the bot contact any voicenotes or audio recordings to get back a written transcription. Uses the OpenAI `whisper-2` model with a temperature setting of 0.7.

- Text to Speech: Send the bot a message starting with `/tts` and then any text you want to have read aloud to get back a voicenote with said text. Find the available voices with `/tts get_voices <search text (optional)>`, choose one with `/tts set_voice <voice name>`, or see which one you have set with `/tts get_voice`. Uses the Text To Speech capabilities of the Azure AI Speech resource.

- Image transcription: Send the bot a picture of any text you need to transcribe (whether a picture of a PDF, or a printed document, or even a handwritten note or sign) and get back all the text detected in the picture. Uses the OCR for images model of the Azure AI Vision resource.

- Image background removal/subject cutout: Send the bot any picture of a subject that you want to cut out from the background and caption it with `/bg <new background color (optional)>` and it'll send you back the cropped cutout. Please note that since WhatsApp doesn't allow transparent images in chats, you'll receive a full image with the background filled with the chosen color. Uses the Segment API of the Azure AI Vision resource.

- Image to ASCII art filter: Send the bot any picture with the caption `/i2a` and any (or none) of the following: `bgcolor=<new background color> w=<width in chars> h=<height in chars> complex negative flipx flipy`. It'll send you back the image converted to white-on-black ASCII art and any additional transformations applied. Uses the [ascii-image-converter utility](https://github.com/TheZoraiz/ascii-image-converter)

## Installation

### Prerequisites

- A DigitalOcean account, the doctl CLI tool, and a DigitalOcean Functions namespace. If you don't have an account, create one by clicking on the badge above. If you don't have the doctl CLI tool, follow this guide. If you have never used DO Functions before, follow this guide up to the Create a Namespace step.

- A Papertrail log destination to log the function output to. If you don't have one, you'll need to log into (or create an account on) Papertrail, [create a new log destination](https://papertrailapp.com/destinations/new) and change the "Accept connections via..." option to Token. Save the token value.

- A Meta Developer app with the WhatsApp product added to it, and a related access token. If you don't have one, follow [this guide](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started) to get started. If you already have one but don't have an access token, follow [this guide](https://developers.facebook.com/docs/whatsapp/business-management-api/get-started#system-users) instead, and save the token value.

- An OpenAI developer account and a related OpenAI project API key. If you don't have an OpenAI developer account, use [this guide](https://platform.openai.com/docs/quickstart?context=python) to get started. Once you're done with the "Account setup" instructions and have created a secret key, save the key value.

- An Azure account with related Speech and Vision resources and their respective keys and secrets. If you don't have them, follow [this guide's prerequisites](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/get-started-text-to-speech?tabs=linux%2Cterminal&pivots=programming-language-rest) to get started and save the SPEECH_KEY and SPEECH_REGION. Then follow [this guide's prerequisites](https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/quickstarts-sdk/image-analysis-client-library-40?tabs=visual-studio%2Clinux&pivots=programming-language-rest-api) and save the subscription key and endpoint.

- A DigitalOcean Spaces resource (or an AWS S3 resource, or any other sort of S3 compatible cloud object storage service). If you don't have any, follow [this guide](https://docs.digitalocean.com/products/spaces/getting-started/quickstart/) to create a Spaces resource, and [this guide](https://docs.digitalocean.com/products/spaces/how-to/manage-access/#access-keys) to create the required keys. You'll need to save down the endpoint, bucket name, key, and secret.

- A Redis database. If you don't have one, you can create one on Upstash's free tier following [this guide](https://upstash.com/docs/redis/overall/getstarted). Once you've created it, save the endpoint, port, and password from the database dashboard.

- This project uses the new inline encrypted dotenv standard. This means that the .env file holds each variable name in plaintext, and each variable value is encrypted (and so the .env file is safe to commit to the repo, while the decryption key is held in a .env.keys file that is added to .gitignore). This is powered by the dotenvx command line utility. If you don't have it, follow [this guide](https://dotenvx.com/docs/install) to install it.

### Setup

- Clone this repo

- Log into your DigitalOcean account.

- Open the `.env` file and swap the encrypted values with your own values.

  - PAPERTRAIL_TOKEN: Must be your papertrail token.

  - VERIFICATION_TOKEN: Can be any value you want. Any word with 8 or more letters suffices.

  - GRAPH_API_TOKEN: Must be your Meta Graph API token.

  - OPENAI_API_KEY: Must be your OpenAI API token.

  - MS_SPEECH_REGION: Must be your Azure Speech region.

  - MS_SPEECH_KEY: Must be your Azure Speech API key.

  - MS_VISION_KEY: Must be your Azure Vision API key.

  - MS_VISION_ENDPOINT: Must be your Azure Vision endpoint.

  - SYSLOG_HOST: Must be a syslog server host, to receive your application logs.

  - SYSLOG_PORT: Must be the port where the above server will listen for incoming logs.

  - STORAGE_ENDPOINT: Must be the Spaces/S3 endpoint URL.

  - STORAGE_NAME: Must be the Spaces/S3 bucket name.

  - STORAGE_KEY: Must be the Spaces/S3 access key.

  - STORAGE_SECRET: Must be the Spaces/S3 access secret.

  - REDIS_HOST: Must be the Redis server URL.

  - REDIS_PORT: Must be the Redis server port.

  - REDIS_PASSWORD: Must be the Redis server password.

  - FUNCTIONS_ENDPOINT: Must be your designated functions endpoint.

  - FUNCTIONS_NAMESPACE: Must be the functions namespace you created.

  - ASCII_ART_API_SECRET: Can be any value you want. Any word with 8 or more letters suffices. Do not use the same value as VERIFICATION_TOKEN.

- Deploy the functions by running `doctl serverless deploy .` on the repo root directory.

- Get the deployment URL by running `doctl sls fn get whatsapp/webhook --url`. This is the URL you need to supply to your Meta app under App Dashboard -> WhatsApp -> Configuration -> Webhook -> Edit in the Callback URL field, and then in the Verify token field you must supply the same `VERIFICATION_TOKEN` from the `.env` file. Then click `Verify and save`

- Back in the Configuration page, click Manage to launch the App Dashboard Webhook Fields dialog and click Subscribe under the messages webhoook event.

- Finally, go to the API Setup page and under Send and receive messages -> Step 1: Select phone numbers click in the To dropdown and then click in Manage phone number list. Finally, click in Add phone number and follow the instructions on screen to add your phone number to the approved recipients.

- Done! Run the command under Step 2: Send messages with the API to send a message from the bot to yourself, and test your deployment by sending a message back to the bot. You should see a welcome message for any texts you send, and the transcription of any audios or voice notes you send to it.

## TODO

- Microsoft has announced the deprecation of their Segment API. The background removal tool will have to be redone with a different service by Jan 25th, 2025 at the latest.

## License

This code is open sourced under the [MIT license](LICENSE.md)
