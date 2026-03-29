self.addEventListener('install',function(){self.skipWaiting();});
self.addEventListener('activate',function(e){e.waitUntil(clients.claim());});
self.addEventListener('push',function(e){e.waitUntil(self.registration.showNotification('SpotEasy',{icon:'/static/icons/icon-192.png'}));});
