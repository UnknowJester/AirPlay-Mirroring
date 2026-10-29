# AirPlay Mirroring Receiver per Windows (Open Source - Senza Limiti)

Ricevitore AirPlay ad alte prestazioni per Windows 10 e 11.
Permette di duplicare lo schermo di iPhone, iPad e Mac sul computer con audio sincronizzato a 60 FPS e accelerazione hardware Direct3D 11, senza limiti di tempo, senza watermark e completamente gratuito.

---

## ✨ Funzionalità Principali (v1.1)

- 📱 **Interfaccia Grafica Moderna & Intuitiva**: Pannello di controllo completo con monitoraggio dello stato in tempo reale, guida visiva e gestione avanzata.
- ⚡ **Ottimizzazione Bassa Latenza (Zero-Lag)**:
  - Disattivazione del timestamp buffering (`-vsync no`) per una visualizzazione istantanea dei fotogrammi video.
  - Buffer audio a bassa latenza (`-al 0.1` / 100ms) per la massima reattività.
  - Frequenza fotogrammi a **60 FPS** stabili.
- 🔒 **Protezione con Codice PIN a 4 Cifre**:
  - Possibilità di richiedere l'inserimento di un PIN di sicurezza sull'iPhone prima di autorizzare la duplicazione dello schermo.
  - Generatore di PIN casuale integrato con un clic (`🎲 Genera PIN`).
- 📺 **Scelta della Risoluzione e Fluidità**:
  - **1080p (Full HD - 1920x1080 @ 60 FPS)**: Modalità standard ad altissima definizione.
  - **720p (Massima Fluidità - 1280x720 @ 60 FPS)**: Ottimale per reti Wi-Fi congestionate o PC con risorse ridotte.
  - **4K (Ultra HD - 3840x2160 @ 60 FPS)**: Massima nitidezza visiva con decodifica hardware H.265 (HEVC).
- 🔄 **Orientamento dello Schermo**:
  - Supporto per la rotazione del flusso video a 90° orario, 90° antiorario o inversione a 180° (ideale per monitor verticali).
- 🔊 **Controllo Audio Integrato**:
  - Possibilità di abilitare o disabilitare l'audio dell'iPhone sugli altoparlanti del PC (modalità solo video `-as 0`).
- 🪟 **Schermo Intero Automatico**:
  - Opzione per avviare il video direttamente a tutto schermo (`-fs`).
- 🟢 **Rilevamento Connessione in Tempo Reale**:
  - Indicatore dinamico dello stato della trasmissione che mostra se il server è in ascolto o se un iPhone è connesso, riportandone l'indirizzo IP locale.
- 💾 **Configurazione Persistente**:
  - Tutte le impostazioni e personalizzazioni vengono salvate localmente in `config.json` e ripristinate automaticamente ad ogni avvio.
- 🛡️ **Zero Avvio Automatico & Chiusura Pulita al 100%**:
  - L'applicazione **non si avvia mai da sola all'accensione del PC**.
  - Si avvia **esclusivamente quando lo decidi tu**.
  - Chiusura garantita al 100% tramite **Windows Job Object**: chiudendo la finestra, tutti i processi del motore e i demoni di rete vengono arrestati all'istante, senza lasciare processi residui in background.

---

## 🚀 Come avviare e usare l'app

1. Fai doppio clic su **`AirPlay.exe`** (oppure sul collegamento Desktop **AirPlay**).
2. Si aprirà la finestra di controllo: il ricevitore si attiverà automaticamente in modalità **IN ASCOLTO** (indicatore giallo).
3. Prendi il tuo iPhone/iPad (assicurati che sia connesso alla **stessa rete Wi-Fi** del computer):
   - Apri il **Centro di Controllo** (scorri verso il basso dall'angolo in alto a destra dello schermo).
   - Tocca l'icona **Duplica schermo** (i due rettangoli sovrapposti).
   - Seleziona il nome del tuo computer (predefinito: **`AirPlay4979`** o quello da te configurato).
   - Se hai attivato il PIN di sicurezza, digita le 4 cifre mostrate nella finestra del programma.
4. La schermata del telefono apparirà istantaneamente sul monitor del computer e l'indicatore diventerà **VERDE (IN TRASMISSIONE)**.
5. Quando hai terminato, premi semplicemente **"⏹ Termina e Chiudi Tutto"** o la **X** della finestra: tutti i processi terminano immediatamente.

---

## ⚙️ Personalizzazione delle Impostazioni

Dalla scheda **"⚙️ Impostazioni"** puoi configurare a piacimento:
- **Nome Ricevitore AirPlay**: Modifica il nome con cui il PC appare nei dispositivi Apple della rete.
- **PIN di Sicurezza**: Attiva o disattiva la richiesta di PIN e imposta il codice desiderato.
- **Risoluzione & FPS**: Scegli tra 1080p, 720p o 4K a 60 FPS o 30 FPS.
- **Bassa Latenza (Zero-Lag)**: Attiva/disattiva le ottimizzazioni per la minima latenza di visualizzazione.
- **Schermo Intero**: Seleziona se aprire il video direttamente a tutto schermo.
- **Orientamento**: Imposta la rotazione video se usi un display verticale.
- Premi **"💾 Salva Impostazioni e Riavvia Ricevitore"** per applicare subito i cambiamenti.

---

## 🛠️ Requisiti di Sistema e Compilazione

- **Sistema Operativo**: Windows 10 o Windows 11 (64-bit).
- **Rete**: Connessione Wi-Fi o Ethernet sulla stessa sottorete locale del dispositivo iOS/macOS.
- **Servizio Bonjour**: Servizio Apple Bonjour (incluso nei componenti di rete standard).
- **Compilazione da sorgente** (facoltativo per sviluppatori):
  ```cmd
  pip install -r requirements.txt
  build.bat
  ```

---

## 📄 Licenza

Rilasciato sotto licenza open source GPL / MIT. Libero per uso personale e professionale senza alcuna limitazione.
