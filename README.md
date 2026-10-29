# AirPlay Mirroring Receiver per Windows (Open Source - Senza Limiti)

Ricevitore AirPlay ad alte prestazioni per Windows 10 e 11.
Permette di duplicare lo schermo di iPhone, iPad e Mac sul computer con audio sincronizzato a 60 FPS e accelerazione hardware Direct3D 11, senza limiti di tempo, senza watermark e completamente gratuito.

---

## 🚀 Come avviare e usare l'app

1. Fai doppio clic sul collegamento **AirPlay** sul Desktop oppure su **`AirPlay.exe`** nella cartella `airplay`.
2. Si aprirà una **finestra di controllo** che ti confermerà che il ricevitore è **ATTIVO** e in ascolto.
3. Prendi il tuo iPhone (assicurati che sia connesso alla **stessa rete Wi-Fi** del PC):
   - Apri il **Centro di Controllo** (scorri verso il basso dall'angolo in alto a destra).
   - Tocca l'icona **Duplica schermo** (i due rettangoli sovrapposti).
   - Seleziona **`AirPlay4979`**.
4. La schermata del telefono apparirà istantaneamente sul monitor del computer.
5. Quando hai finito, basta cliccare **"Chiudi e Termina Ricevitore"** (o la classica **X** della finestra): tutti i processi di streaming e di rete vengono terminati all'istante, senza lasciare nulla attivo in background.

---

## ⚡ Modalità Bassa Latenza (Zero-Lag)

Per impostazione predefinita è attiva l'opzione:
- **`-vsync no`**: disattiva il timestamp buffering (che di default introduce 250ms–1s di ritardo per sincronizzare video e audio da film). Con questa modalità, i frame video vengono decodificati e mostrati a schermo nel millisecondo esatto in cui arrivano via Wi-Fi.
- **`-al 0.1`**: riduce il buffer audio a soli 100ms.
- **`-fps 60`**: richiede a iOS un flusso a 60 frame al secondo stabili.

---

## 🛑 Nessun avvio automatico / Nessun processo nascosto

- L'app **non si avvia mai da sola all'accensione del PC**.
- Si apre solo quando lo decidi tu cliccando sull'icona.
- Chiudendo la finestra di controllo, l'app e il motore si arrestano al 100% senza rimanere nascosti nella barra di sistema.
