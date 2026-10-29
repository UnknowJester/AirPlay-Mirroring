# AirMirroring - AirPlay Receiver per Windows (Open Source - Senza Limiti)

Ricevitore AirPlay ad alte prestazioni per Windows 10 e 11 con interfaccia moderna **AirMirroring** e **incorporamento video nativo** nella stessa finestra dell'applicazione.
Permette di duplicare lo schermo di iPhone, iPad e Mac sul computer con audio sincronizzato a 60 FPS e accelerazione hardware Direct3D 11, senza limiti di tempo, senza watermark e completamente gratuito.

---

## ✨ Nuove Funzionalità (v1.3)

- ⚡ **Zero-Flicker Native Docking (0ms Flash)**:
  - Eliminato completamente qualsiasi sfarfallio o comparsa della vecchia finestra esterna sul desktop all'avvio della connessione.
  - Utilizzo di hook nativo di sistema Win32 (`SetWinEventHook`) con intercettazione immediata a livello kernel/DWM (`SW_HIDE` e `SetParent` istantaneo): il video dello streaming compare direttamente e fluidamente nel contenitore dell'applicazione.
- 🎨 **Schermata Standby Pulita ed Elegante**:
  - Rimossi codici QR e badge store non necessari: AirPlay è nativo sui dispositivi Apple e non richiede app esterne.
  - Nuova scheda centrale minimalista con monitor grafico AirPlay, nome ricevitore in evidenza, codice PIN dinamico (se attivo), animazione a 4 pallini e guida rapida di connessione in 3 passaggi chiari.
- 📺 **Incorporamento Video Diretto (Single-Window All-in-One)**:
  - Il flusso di duplicazione dello schermo viene incorporato direttamente all'interno della finestra principale dell'applicazione (al posto della schermata di standby) tramite Win32 window docking.
  - Quando l'iPhone si connette, la visualizzazione passa fluidamente al video in streaming.
  - Quando il mirroring viene interrotto, l'app torna istantaneamente alla schermata di standby.
  - **Tasto Schermo Intero (`F` o `F11`)**: puoi ingrandire a tutto schermo borderless in qualsiasi momento e tornare indietro con `Esc`.
- ⚙️ **Pannello Impostazioni Avanzato e Completo**:
  - **Nome Ricevitore**: Personalizzazione immediata con sanitizzazione automatica degli spazi (`Pc-dav`) per piena conformità mDNS Apple.
  - **Sicurezza con Codice PIN**: Richiesta obbligatoria di PIN a 4 cifre prima di visualizzare lo schermo, con tasto `🎲 Genera PIN` e visualizzazione prominente in standby.
  - **Qualità Video Selezionabile**: 1080p (Full HD), 720p (Max Fluidità), 1440p (2K Quad HD) e 4K (Ultra HD H.265 / HEVC).
  - **Fluidità (FPS)**: Scelta tra 60 FPS (ultra-fluido) e 30 FPS (risparmio risorse).
  - **Bassa Latenza (Zero-Lag)**: Timestamp buffering disattivato (`-vsync no`) per risposta in tempo reale.
  - **Gestione Audio PC**: Attiva/disattiva l'audio dell'iPhone sugli altoparlanti del PC, con buffer audio configurabile (100ms, 250ms, 500ms) e profilo volume naturale (`-taper`).
  - **Orientamento & Rotazione**: Supporto per ruotare il display di 90° Destra, 90° Sinistra o Capovolto 180° (ideale per display verticali).
  - **Finestra Sempre in Primo Piano**: Opzione `Always on Top` per mantenere il mirroring visibile sopra le altre finestre.
  - **Schermo Intero Automatico**: Opzione per espandere il video a schermo intero automaticamente alla connessione.
- 🛡️ **Zero Avvio Automatico & Chiusura Pulita al 100%**:
  - Nessun demone o servizio in esecuzione all'avvio del computer.
  - Chiusura garantita di tutti i processi in background tramite **Windows Job Object**.

---

## 🚀 Come avviare e usare l'app

1. Fai doppio clic su **`AirPlay.exe`** (oppure sul collegamento Desktop **AirPlay**).
2. Si aprirà la schermata principale di **AirMirroring** con il nome del tuo ricevitore e la guida di connessione rapida.
3. Prendi il tuo iPhone/iPad (connesso alla **stessa rete Wi-Fi** del computer):
   - Apri il **Centro di Controllo** (scorri verso il basso dall'angolo in alto a destra).
   - Tocca l'icona **Duplica schermo** (i due rettangoli sovrapposti).
   - Seleziona **`AirMirroring 【NomeDispositivo】`** (es. `Pc-dav`).
   - Se hai attivato il PIN, inserisci le 4 cifre visualizzate sullo schermo.
4. Il mirroring apparirà **direttamente all'interno della finestra principale**.
5. Premi **`F`** o fai doppio clic per la modalità a tutto schermo, oppure **`Esc`** per uscire.
6. Per modificare le impostazioni, clicca sull'icona **`⚙️`** in basso a destra.
7. Chiudendo la finestra, tutti i processi vengono terminati al 100%.

---

## 🛠️ Requisiti di Sistema e Compilazione

- **Sistema Operativo**: Windows 10 o Windows 11 (64-bit).
- **Rete**: Wi-Fi o Ethernet sulla stessa sottorete locale del dispositivo Apple.
- **Dipendenze Python** (per sviluppo da sorgente):
  ```cmd
  pip install -r requirements.txt
  build.bat
  ```

---

## 📄 Licenza

Rilasciato sotto licenza open source GPL / MIT. Libero per uso personale e professionale senza alcuna limitazione.
