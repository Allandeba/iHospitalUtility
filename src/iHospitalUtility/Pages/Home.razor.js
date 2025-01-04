window.isInStandaloneMode = () => {
    return ('standalone' in window.navigator) && (window.navigator.standalone);
}

function hideInstallAppModal(key) {
    const MAX_DATE = "9999-12-31";

    const base64Value = btoa("true");
    const cacheItem = 
    { 
        Value: base64Value,
        ExpiresAt: MAX_DATE
    };

    const jsonString = JSON.stringify(cacheItem);

    localStorage.setItem(key, jsonString);
    var element = document.getElementById('installAppButton');
    if (element) {
        element.parentElement.parentElement.remove();
    }
}