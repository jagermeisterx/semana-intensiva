# unir-video-BBB

Extensión de Chrome que detecta automáticamente los videos de pantalla compartida (`deskshare.webm`) y webcams (`webcams.webm`) en grabaciones de BigBlueButton, los descarga y los une en un solo archivo con el video de la pantalla y el audio de las webcams.

## Requisitos

- [ffmpeg](https://ffmpeg.org/) instalado y accesible en el PATH
- Chrome / Chromium (versión 88+)

## Instalación

### 1. Instalar ffmpeg

```bash
# Linux (Debian/Ubuntu)
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
winget install ffmpeg
```

Verifica con: `ffmpeg -version`

### 2. Cargar la extensión en Chrome

1. Abre `chrome://extensions`
2. Activa **"Modo desarrollador"** (esquina superior derecha)
3. Haz clic en **"Cargar descomprimida"**
4. Selecciona la carpeta `bbb-merge-extension/` de este proyecto
5. La extensión aparecerá como **BBB Merge**
6. Anota el **ID de extensión** que aparece bajo el nombre (ej: `abcdefghijklmnopqrst`)

### 3. Instalar el host nativo

```bash
cd bbb-merge-extension/native-host
bash install.sh
```

El script te pedirá el ID de la extensión que anotaste en el paso anterior. También puedes pasarlo como argumento:

```bash
bash install.sh <tu-extension-id>
```

#### Windows

```cmd
cd bbb-merge-extension\native-host
install.bat
```

### 4. Recargar la extensión

En `chrome://extensions`, haz clic en el icono de recarga 🔄 de **BBB Merge**.

## Uso

1. Abre cualquier grabación de BigBlueButton en tu navegador
2. La extensión detecta automáticamente los videos de la página
3. Aparecerá un badge `1` en el ícono de la extensión en la barra de herramientas
4. Haz clic en el ícono para abrir el popup
5. Revisa los videos detectados y haz clic en **"🔀 Unir y descargar"**
6. El progreso se muestra en el popup:
   - 📥 Descarga de deskshare.webm
   - 📥 Descarga de webcams.webm
   - 🔀 Unión con ffmpeg
   - ✅ Archivo guardado en `~/Downloads/BBB_merged_<timestamp>.webm`

## Comportamiento

| Situación | Resultado |
|-----------|-----------|
| deskshare + webcams disponibles | Video de pantalla + audio de webcams |
| Solo webcams.webm | Se copia el archivo tal cual |
| Solo deskshare.webm | Se copia el archivo (sin audio) |
| Ningún video detectado | Error: "No hay videos detectados" |

## Estructura del proyecto

```
bbb-merge-extension/
├── manifest.json                # Manifiesto de la extensión Chrome
├── popup.html / popup.css       # Interfaz del popup
├── icons/                       # Iconos de la extensión
├── src/
│   ├── content.js               # Detecta videos en páginas BBB
│   ├── background.js            # Service Worker (Native Messaging)
│   └── popup.js                 # Lógica del popup
└── native-host/
    ├── com.bbb.merge.json       # Manifiesto del host nativo (plantilla)
    ├── bbb-merge-host.py        # Script Python que descarga y une
    ├── install.sh               # Instalación Linux/macOS
    └── install.bat              # Instalación Windows
```