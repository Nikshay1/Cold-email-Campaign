# Cortexa Labs — Cold Email Automation Engine

> **A beautifully simple, template-based cold email platform** built to automatically distribute your outreach campaigns across multiple Gmail accounts to ensure high deliverability and zero spam flags.

---

## 🚀 What This Does

- **Upload Leads:** Drop in a CSV file with your prospects' names and emails.
- **Connect Gmails:** Link as many Gmail or Google Workspace accounts as you want.
- **Write Templates:** Draft a single email using tags like `[NAME]` or `[COMPANY]` and the system will automatically personalize every single email.
- **Inbox Rotation (Round-Robin):** If you upload 1,000 leads and select 4 sender inboxes, the system will perfectly divide the work, sending exactly 250 emails from each account to keep your sending limits perfectly safe.
- **Read Replies:** The system automatically checks your connected inboxes and pulls all replies perfectly into a centralized dashboard!

---

## 🛠️ Step 1: Getting Started

You only need to do this once to boot up the system on your computer.

1. Open your terminal in this folder.
2. Ensure Docker Desktop is open and running on your computer.
3. Run the following command exactly as written:
   ```bash
   docker compose up --build -d
   ```
4. Wait a minute for it to finish booting up.

Your application is now live! 
👉 **Open your browser and jump into the dashboard:** [http://localhost:3000](http://localhost:3000)

---

## ⚙️ Step 2: Configure Google (One-Time Setup)

To allow the platform to physically send emails through your Gmail accounts, you just need a standard Google Cloud App set up.

1. Go to the [Google Cloud Console](https://console.cloud.google.com).
2. Create a new project and enable the **Gmail API**.
3. Go to **APIs & Services > OAuth consent screen** and set up an External app (add your own email as a Test User).
4. Go to **Credentials**, click **Create Credentials**, and select **OAuth client ID** (Web application).
5. Add the following to **Authorized redirect URIs**:
   ```
   http://localhost:8000/auth/google/callback
   ```
6. Open the hidden `.env` file in the root of this project folder and paste your new keys:
   ```env
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

*(Restart your terminal `docker compose down && docker compose up -d` if you edit the .env file).*

---

## 📧 Step 3: Connect Your Senders

Now let's add the actual Gmail accounts that will do the sending.

1. Go to **[Inboxes](http://localhost:3000/inboxes)** in the Dashboard.
2. Type in the Email Address (e.g. `nikshayyadav90@gmail.com`), your Display Name, and click **Connect**.
3. You will be redirected to Google to click "Allow". 
4. Once you return, the inbox will show a green `GOOD` health status! You can connect as many as you want.

---

## 👥 Step 4: Upload Your Prospects

1. Go to **[Leads](http://localhost:3000/leads)** -> Click **Upload CSV**.
2. Upload your list. 
   - *Note: Your CSV spreadsheet must have the headers `first_name` and `email` for the system to read them correctly.*

*(A testing sample CSV is already available for you inside the `backend/tests/fixtures/sample_leads.csv` folder!)*

---

## 🎯 Step 5: Launch Your Campaign

The magic happens here. We will distribute your emails gently so you never get blocked by Google.

1. Go to **[Campaigns](http://localhost:3000/campaigns)** -> Click **New Campaign**.
2. Give your campaign a name.
3. **Select Sender Inboxes:** You will see a checklist of all the Gmails you connected in Step 3. Check the ones you want to use. The system will evenly divide the emails across the ones you select!
4. **Subject Line:** Write your subject. You can use tags! Example: `Quick question for [NAME]`
5. **Email Body:** Write your email. 
   ```text
   Hi [NAME],

   I saw that [COMPANY] is doing some great work. I'd love to chat.

   Best,
   Nikshay
   ```
6. Click **Launch Sequence**! 
7. The system will now begin actively sending the emails in the background. It will automatically space the emails out by a few minutes each to ensure your account stays completely safe from spam filters. 

---

## 📬 Step 6: Monitor Replies

You don't need to log into 5 different Gmail accounts to check for replies anymore!
1. The backend automatically reads your connected Gmail inboxes every few minutes.
2. Go to **[Replies](http://localhost:3000/replies)**.
3. Every single reply from your prospects will appear right here in a unified inbox feed for you to read.

---
*Built by Cortexa Labs*