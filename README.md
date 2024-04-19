# WhatsApp Voicenote Transcriber

This project is a Python project that uses the WhatsApp Business Platform Cloud API and the OpenAI speech-to-text Whisper 2 Model to return the transcription of any audio messages and voice notes that you send to it.

This project is hosted in the DigitalOcean Functions free tier. Get a $200 credit for 60 days by clicking on the badge below.

[![DigitalOcean Referral Badge](https://web-platforms.sfo2.cdn.digitaloceanspaces.com/WWW/Badge%201.svg)](https://www.digitalocean.com/?refcode=d1b30a7a0c5b&utm_campaign=Referral_Invite&utm_medium=Referral_Program&utm_source=badge)

## Installation

### Prerequisites

- A DigitalOcean account, the `doctl` CLI tool, and a DigitalOcean Functions namespace. If you don't have an account, create one by clicking on the badge above. If you don't have the `doctl` CLI tool, follow [this guide](https://docs.digitalocean.com/reference/doctl/how-to/install/). If you have never used DO Functions before, follow [this guide](https://docs.digitalocean.com/products/functions/getting-started/quickstart) up to the Create a Namespace step.

- A Papertrail log destination to log the function output to. If you don't have one, you'll need to log into (or create an account on) Papertrail, [create a new log destination](https://papertrailapp.com/destinations/new) and change the "Accept connections via..." option to Token. Save the token value.

- A Meta Developer app with the WhatsApp product added to it, and a related access token. If you don't have one, follow [this guide](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started) to get started. If you already have one but don't have an access token, follow [this guide](https://developers.facebook.com/docs/whatsapp/business-management-api/get-started#system-users) instead, and save the token value.

- A OpenAI developer account and a related OpenAI project API key. If you don't have an OpenAI developer account, use [this guide](https://platform.openai.com/docs/quickstart?context=python) to get started. Once you're done with the "Account setup" instructions and have created a secret key, save the key value.

### Setup

- Clone this repo

- Log into your DigitalOcean account.

- Rename the `.env.template` file to `.env` and fill in the blanks

  - `VERIFICATION_TOKEN` can be any value you want

  - `PAPERTRAIL_TOKEN` needs to be your Papertrail log destination token.

  - `GRAPH_API_TOKEN` must be your Meta app access token.

  - `OPENAI_API_KEY` has to be your OpenAI API key.

- Deploy the function by running `doctl serverless deploy .` on the repo root directory.

- Get the deployment URL by running `doctl sls fn get whatsapp/webhook --url`. This is the URL you need to supply to your Meta app under App Dashboard -> WhatsApp -> Configuration -> Webhook -> Edit in the Callback URL field, and then in the Verify token field you must supply the same `VERIFICATION_TOKEN` from the `.env` file. Then click `Verify and save`

- Back in the Configuration page, click Manage to launch the App Dashboard Webhook Fields dialog and click Subscribe under the messages webhoook event.

- Finally, go to the API Setup page and under Send and receive messages -> Step 1: Select phone numbers click in the To dropdown and then click in Manage phone number list. Finally, click in Add phone number and follow the instructions on screen to add your phone number to the approved recipients.

- Done! Run the command under Step 2: Send messages with the API to send a message from the bot to yourself, and test your deployment by sending a message back to the bot. You should see a welcome message for any texts you send, and the transcription of any audios or voice notes you send to it.

## License

This code is open sourced under the [MIT license](https://github.com/isthistechsupport/whatsapp-vn-transcriber/blob/main/LICENSE.md)
