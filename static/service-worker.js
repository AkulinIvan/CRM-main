self.addEventListener('push', function(event) {
    let notificationData = {};
    try {
        notificationData = event.data.json();
    } catch (e) {
        notificationData = {
            title: 'Новое уведомление',
            body: event.data.text(),
        };
    }

    const options = {
        body: notificationData.body,
        icon: notificationData.icon || '/static/images/notification-icon.png',
        badge: notificationData.badge || '/static/images/notification-badge.png',
        data: {
            url: notificationData.url || '/'
        }
    };

    event.waitUntil(
        self.registration.showNotification(notificationData.title, options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.matchAll({type: 'window'}).then(windowClients => {
            for (const client of windowClients) {
                if (client.url === event.notification.data.url && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(event.notification.data.url);
            }
        })
    );
});