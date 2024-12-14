const {app, BrowserWindow, dialog, session} = require('electron');
const path = require('path');

let mainWindow;

async function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1600,
        height: 1000,
        title: 'Cyber Range',
        icon: path.join(__dirname, 'tarIco.ico'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: false
        }
    });

    try {
        await mainWindow.loadURL('http://localhost:8000/');
    } catch (error) {

        dialog.showErrorBox('Connection Error', 
            'Failed to connect to the server. ');
        mainWindow = null;
        app.quit();
        return;
    }

    mainWindow.on('close', async (e) => {
        e.preventDefault();

        const {response} = await dialog.showMessageBox({
            type: 'question',
            title: 'Confirm Exit',
            message: 'Are you sure you want to exit?',
            buttons: ['Yes', 'No'],
            defaultId: 1,
            cancelId: 1,
            noLink: true,
            normalizeAccessKeys: true
        });

        if (response === 1) {
            e.preventDefault();
        } else {
            try {
                await session.defaultSession.clearCache();

                await session.defaultSession.clearStorageData({
                    storages: [
                        'cookies',
                        'localStorage',
                        'sessionStorage',
                    ]
                });

                mainWindow = null;
                app.exit();
            } catch (error) {
                dialog.showErrorBox('Error', `Failed to clear session: ${error.message}`);
                mainWindow = null;
                app.exit();
            }
        }
    });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    app.quit();
});

process.on('uncaughtException', (error) => {
    dialog.showErrorBox('Error', `An unexpected error occurred: ${error.message}`);
});