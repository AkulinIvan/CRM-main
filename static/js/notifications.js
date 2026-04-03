// static/js/notifications.js

// Регистрация Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/service-worker.js')
            .then(registration => {
                console.log('ServiceWorker registration successful');
            })
            .catch(err => {
                console.log('ServiceWorker registration failed: ', err);
            });
    });
}

// Функция подписки на уведомления
function subscribeToPushNotifications() {
    if (!('serviceWorker' in navigator)) {
        console.warn('Service workers are not supported');
        return;
    }

    if (!('PushManager' in window)) {
        console.warn('Push notifications are not supported');
        return;
    }

    navigator.serviceWorker.ready.then(registration => {
        return registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array('{{ VAPID_PUBLIC_KEY }}')
        });
    }).then(subscription => {
        // Отправляем подписку на сервер
        return fetch('/api/notifications/subscribe/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify(subscription),
        });
    }).then(response => {
        if (!response.ok) {
            throw new Error('Failed to save subscription');
        }
        return response.json();
    }).then(data => {
        console.log('Successfully subscribed to push notifications');
    }).catch(error => {
        console.error('Error subscribing to push notifications:', error);
    });
}

// Функция отписки от уведомлений
function unsubscribeFromPushNotifications() {
    navigator.serviceWorker.ready.then(registration => {
        return registration.pushManager.getSubscription();
    }).then(subscription => {
        if (subscription) {
            // Отправляем запрос на сервер для удаления подписки
            return fetch('/api/notifications/unsubscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({
                    endpoint: subscription.endpoint
                }),
            }).then(() => subscription.unsubscribe());
        }
    }).then(() => {
        console.log('Successfully unsubscribed from push notifications');
    }).catch(error => {
        console.error('Error unsubscribing from push notifications:', error);
    });
}

// Вспомогательная функция для преобразования ключа
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// Вспомогательная функция для получения CSRF токена
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Кнопка включения/отключения уведомлений
    const notificationToggle = document.getElementById('notification-toggle');
    if (notificationToggle) {
        notificationToggle.addEventListener('change', function() {
            if (this.checked) {
                subscribeToPushNotifications();
            } else {
                unsubscribeFromPushNotifications();
            }
        });
    }
    
    // Проверяем текущий статус подписки
    checkSubscriptionStatus();
});

// Проверка статуса подписки
function checkSubscriptionStatus() {
    navigator.serviceWorker.ready.then(registration => {
        return registration.pushManager.getSubscription();
    }).then(subscription => {
        const toggle = document.getElementById('notification-toggle');
        if (toggle) {
            toggle.checked = !!subscription;
        }
    }).catch(error => {
        console.error('Error checking subscription status:', error);
    });
}