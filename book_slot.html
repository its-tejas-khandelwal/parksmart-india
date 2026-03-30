// ═══════════════════════════════════════════════════════════════════
//   SpotEasy India — Live Auto-Refresh + Browser Notifications
//   Works for Admin, Vendor, and Customer dashboards
// ═══════════════════════════════════════════════════════════════════

var SpotEasyLive = {
  role: null,
  userId: null,
  lastPendingVendors: -1,
  lastPendingLots: -1,
  lastActiveBookings: -1,

  // ── Request browser notification permission ──────────────────────
  requestNotifications: function() {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  },

  // ── Show browser notification ────────────────────────────────────
  notify: function(title, body, icon) {
    if ('Notification' in window && Notification.permission === 'granted') {
      var n = new Notification(title, {
        body: body,
        icon: icon || '/static/icons/icon-192.png',
        badge: '/static/icons/icon-72.png',
        tag: 'spoteasy-' + Date.now(),
      });
      n.onclick = function() { window.focus(); n.close(); };
      setTimeout(function() { n.close(); }, 6000);
    }
  },

  // ── Update element text silently ─────────────────────────────────
  update: function(id, val) {
    var el = document.getElementById(id);
    if (el && el.textContent != String(val)) {
      el.textContent = val;
      el.style.transition = 'color 0.3s';
      el.style.color = '#16a34a';
      setTimeout(function() { el.style.color = ''; }, 800);
    }
  },

  // ── Update badge (pending count) ─────────────────────────────────
  badge: function(id, count) {
    var el = document.getElementById(id);
    if (!el) return;
    if (count > 0) {
      el.textContent = count;
      el.style.display = 'inline-block';
    } else {
      el.style.display = 'none';
    }
  },

  // ── ADMIN: Poll every 5 seconds ──────────────────────────────────
  pollAdmin: function() {
    var self = this;
    fetch('/api/admin/stats', {cache: 'no-store'})
      .then(function(r) { return r.json(); })
      .then(function(d) {
        // Update stats
        self.update('statTotalUsers',    d.total_users);
        self.update('statTotalLots',     d.total_lots);
        self.update('statActiveBookings',d.active_bookings);
        self.update('statRevenue',       '₹' + Math.round(d.total_revenue));

        // Pending badges
        self.badge('badgePendingVendors', d.pending_vendors);
        self.badge('badgePendingLots',    d.pending_lots);

        // Notify if NEW pending vendor appeared
        if (self.lastPendingVendors >= 0 && d.pending_vendors > self.lastPendingVendors) {
          var newV = d.new_vendors[0];
          self.notify(
            'New Vendor Request!',
            (newV ? newV.name : 'A vendor') + ' is waiting for approval.',
          );
        }
        // Notify if NEW pending lot appeared
        if (self.lastPendingLots >= 0 && d.pending_lots > self.lastPendingLots) {
          var newL = d.new_lots[0];
          self.notify(
            'New Lot Pending Approval!',
            (newL ? newL.name + ', ' + newL.city : 'A lot') + ' needs approval.',
          );
        }

        self.lastPendingVendors = d.pending_vendors;
        self.lastPendingLots    = d.pending_lots;
      })
      .catch(function() {});
  },

  // ── VENDOR: Poll every 3 seconds ─────────────────────────────────
  pollVendor: function(vid) {
    var self = this;
    fetch('/api/vendor/stats/' + vid, {cache: 'no-store'})
      .then(function(r) { return r.json(); })
      .then(function(d) {
        self.update('statFreeSlots',     d.free_slots);
        self.update('statOccupied',      d.occupied_slots);
        self.update('statActiveBookings',d.active_bookings);
        self.update('statRevenue',       '₹' + Math.round(d.total_revenue));

        // Notify if new booking arrived
        if (self.lastActiveBookings >= 0 && d.active_bookings > self.lastActiveBookings) {
          self.notify('New Booking!', 'A customer just booked a slot at your lot.');
        }
        self.lastActiveBookings = d.active_bookings;

        // Update individual lot counts
        if (d.lots) {
          d.lots.forEach(function(lot) {
            self.update('lotFree-' + lot.id,     lot.free);
            self.update('lotOccupied-' + lot.id, lot.occupied);
          });
        }
      })
      .catch(function() {});
  },

  // ── CUSTOMER: Poll every 15 seconds ──────────────────────────────
  pollCustomer: function() {
    var self = this;
    fetch('/api/customer/stats', {cache: 'no-store'})
      .then(function(r) { return r.json(); })
      .then(function(d) {
        self.update('statActive',    d.active || 0);
        self.update('statCompleted', d.completed || 0);
        self.update('statTotal',     d.total_bookings || 0);
        self.update('statSpent',     '₹' + (d.total_spent || 0));

        // Show live dot if active booking
        var dot = document.getElementById('liveDot');
        if (dot) dot.style.display = (d.active > 0) ? 'inline-block' : 'none';

        // Notify if booking completed
        if (self.lastActiveBookings >= 0 &&
            d.active < self.lastActiveBookings && d.active === 0) {
          self.notify('Checkout Complete!', 'Your parking session has ended.');
        }
        self.lastActiveBookings = d.active || 0;
      })
      .catch(function() {});
  },

  // ── LOT GRID: Poll every 3 seconds ───────────────────────────────
  pollLotGrid: function(lotId) {
    var self = this;
    fetch('/api/lot/' + lotId + '/slots', {cache: 'no-store'})
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var slots = data.slots || data;
        slots.forEach(function(slot) {
          var el = document.getElementById('slot-' + slot.id);
          if (!el) return;
          var occupied = slot.is_occupied || slot.status === 'occupied';
          el.className = el.className.replace(/slot-available|slot-occupied/g, '');
          el.classList.add(occupied ? 'slot-occupied' : 'slot-available');
          var statusEl = el.querySelector('.slot-status');
          if (statusEl) statusEl.textContent = occupied ? 'Occupied' : 'Free';
        });
        // Update counts
        var free2w = slots.filter(function(s){return (s.slot_type||s.type)==='2w'&&!s.is_occupied&&s.status!=='occupied';}).length;
        var free4w = slots.filter(function(s){return (s.slot_type||s.type)==='4w'&&!s.is_occupied&&s.status!=='occupied';}).length;
        var occ2w  = slots.filter(function(s){return (s.slot_type||s.type)==='2w'&&(s.is_occupied||s.status==='occupied');}).length;
        var occ4w  = slots.filter(function(s){return (s.slot_type||s.type)==='4w'&&(s.is_occupied||s.status==='occupied');}).length;
        self.update('avail2w', free2w);
        self.update('avail4w', free4w);
        self.update('occ2w',   occ2w);
        self.update('occ4w',   occ4w);

        // Update countdown
        var indicator = document.getElementById('liveIndicator');
        if (indicator) indicator.style.opacity = '1';
      })
      .catch(function() {});
  },

  // ── Start polling based on role ───────────────────────────────────
  start: function(config) {
    var self = this;
    this.role   = config.role;
    this.userId = config.userId;

    // Request notification permission
    this.requestNotifications();

    if (config.role === 'admin') {
      self.pollAdmin();
      setInterval(function() { self.pollAdmin(); }, 5000);
    }
    else if (config.role === 'vendor') {
      self.pollVendor(config.userId);
      setInterval(function() { self.pollVendor(config.userId); }, 5000);
    }
    else if (config.role === 'customer') {
      self.pollCustomer();
      setInterval(function() { self.pollCustomer(); }, 15000);
    }
    else if (config.role === 'lot_grid') {
      // Countdown timer for lot grid
      var countdown = 3;
      self.pollLotGrid(config.lotId);
      setInterval(function() {
        countdown--;
        var el = document.getElementById('refreshCountdown');
        if (el) el.textContent = countdown + 's';
        if (countdown <= 0) {
          countdown = 3;
          self.pollLotGrid(config.lotId);
        }
      }, 1000);
    }
  }
};
