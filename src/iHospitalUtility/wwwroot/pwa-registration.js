(() => {
    const status = document.getElementById('offline-status');
    const show = (state, message) => {
        status.dataset.offlineState = state;
        status.textContent = message;
    };
    if (!('serviceWorker' in navigator)) {
        show('unavailable', 'Uso offline indisponível neste navegador.');
        return;
    }

    let registration;
    let checkId = 0;
    let ready = false;
    const checkReady = () => {
        const controller = navigator.serviceWorker.controller;
        if (!controller) return;
        const id = ++checkId;
        const channel = new MessageChannel();
        const timer = setTimeout(() => {
            channel.port1.close();
            if (id !== checkId || ready) return;
            show('unavailable', registration?.waiting
                ? 'Atualização pronta. Feche todas as abas do aplicativo e abra novamente.'
                : 'Offline ainda não está pronto. Conecte-se e abra o aplicativo novamente.');
        }, 5000);
        channel.port1.onmessage = event => {
            clearTimeout(timer);
            channel.port1.close();
            if (id !== checkId || event.data?.type !== 'OFFLINE_STATUS') return;
            ready = event.data.ready === true;
            show(ready ? 'ready' : 'unavailable', ready
                ? (registration?.waiting ? 'Disponível offline. Atualização será aplicada na próxima abertura.' : 'Disponível offline.')
                : (event.data.development ? 'Uso offline disponível na versão publicada.' : 'Offline ainda não está pronto. Conecte-se e abra o aplicativo novamente.'));
        };
        controller.postMessage({ type: 'GET_OFFLINE_STATUS' }, [channel.port2]);
    };
    const watchInstall = worker => {
        if (!worker) return;
        worker.addEventListener('statechange', () => {
            if (worker.state === 'installed') checkReady();
            if (worker.state === 'redundant' && !ready) {
                show('unavailable', 'Não foi possível preparar o uso offline. Verifique sua conexão e recarregue.');
            }
        });
    };
    navigator.serviceWorker.addEventListener('controllerchange', checkReady);
    navigator.serviceWorker.register('pwabuilder-sw.js', { updateViaCache: 'none' })
        .then(value => {
            registration = value;
            watchInstall(value.installing);
            value.addEventListener('updatefound', () => watchInstall(value.installing));
            navigator.serviceWorker.ready.then(checkReady);
            checkReady();
        })
        .catch(() => show('unavailable', 'Não foi possível preparar o uso offline. Verifique sua conexão e recarregue.'));
})();
