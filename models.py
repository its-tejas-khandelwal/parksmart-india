{% extends "base.html" %}
{% block title %}Book Slot — {{ lot.name }}{% endblock %}
{% block content %}
<div class="max-w-2xl mx-auto">
  <a href="{{ url_for('lots_list') }}" class="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 mb-5">
    <i data-lucide="arrow-left" class="w-4 h-4"></i> Back to Lots
  </a>

  <div class="card shadow-2xl animate-scale-in">
    <!-- Lot Header -->
    <div class="flex items-start justify-between mb-6 pb-5 border-b border-gray-100 dark:border-dark-700">
      <div>
        <h1 class="text-2xl font-black text-gray-900 dark:text-white">{{ lot.name }}</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-1">
          <i data-lucide="map-pin" class="w-3.5 h-3.5"></i> {{ lot.address }}, {{ lot.city }}
        </p>
      </div>
      <div class="text-right shrink-0 ml-3">
        <div class="text-sm font-bold text-green-600 dark:text-green-400">{{ slots|length }} slots free</div>
      </div>
    </div>

    <!-- Rate Cards -->
    <div class="grid grid-cols-2 gap-3 mb-6">
      <div class="bg-amber-50 dark:bg-amber-900/20 rounded-2xl p-3 text-center border border-amber-200 dark:border-amber-800">
        <div class="text-2xl mb-1">🛵</div>
        <div class="font-black text-xl text-amber-700 dark:text-amber-300">₹{{ lot.rate_2w }}<span class="text-sm font-medium">/hr</span></div>
        <div class="text-xs text-gray-500 mt-0.5">2-Wheeler</div>
      </div>
      <div class="bg-blue-50 dark:bg-blue-900/20 rounded-2xl p-3 text-center border border-blue-200 dark:border-blue-800">
        <div class="text-2xl mb-1">🚗</div>
        <div class="font-black text-xl text-blue-700 dark:text-blue-300">₹{{ lot.rate_4w }}<span class="text-sm font-medium">/hr</span></div>
        <div class="text-xs text-gray-500 mt-0.5">4-Wheeler</div>
      </div>
    </div>

    {% if slots %}
    <form method="POST" id="bookForm">

      <!-- Slot Grid -->
      <div class="mb-6">
        <label class="block text-sm font-black text-gray-700 dark:text-gray-300 mb-3">
          Select a Slot
          <span id="slotTypeHint" class="ml-2 text-xs font-normal text-gray-400">← click to select</span>
        </label>

        <!-- 2W Slots -->
        {% set slots_2w = slots|selectattr('slot_type','eq','2w')|list %}
        {% if slots_2w %}
        <p class="text-xs font-semibold text-amber-600 dark:text-amber-400 mb-2">🛵 2-Wheeler Slots</p>
        <div class="grid grid-cols-5 sm:grid-cols-8 gap-2 mb-4">
          {% for slot in slots_2w %}
          <label class="cursor-pointer group">
            <input type="radio" name="slot_id" value="{{ slot.id }}"
                   data-type="2w" class="peer hidden slot-radio" required/>
            <div class="slot-available peer-checked:!bg-amber-500 peer-checked:!border-amber-500 peer-checked:!text-white rounded-xl p-2 text-center text-xs font-bold transition-all hover:scale-110 group-hover:shadow-md peer-checked:scale-110 peer-checked:shadow-lg">
              <div class="text-base">🛵</div>
              <div>{{ slot.label }}</div>
            </div>
          </label>
          {% endfor %}
        </div>
        {% endif %}

        <!-- 4W Slots -->
        {% set slots_4w = slots|selectattr('slot_type','eq','4w')|list %}
        {% if slots_4w %}
        <p class="text-xs font-semibold text-blue-600 dark:text-blue-400 mb-2">🚗 4-Wheeler Slots</p>
        <div class="grid grid-cols-5 sm:grid-cols-8 gap-2">
          {% for slot in slots_4w %}
          <label class="cursor-pointer group">
            <input type="radio" name="slot_id" value="{{ slot.id }}"
                   data-type="4w" class="peer hidden slot-radio" required/>
            <div class="slot-available peer-checked:!bg-blue-500 peer-checked:!border-blue-500 peer-checked:!text-white rounded-xl p-2 text-center text-xs font-bold transition-all hover:scale-110 group-hover:shadow-md peer-checked:scale-110 peer-checked:shadow-lg">
              <div class="text-base">🚗</div>
              <div>{{ slot.label }}</div>
            </div>
          </label>
          {% endfor %}
        </div>
        {% endif %}
      </div>

      <!-- Vehicle Type (auto-selected, read-only display) -->
      <div class="mb-5">
        <label class="block text-sm font-black text-gray-700 dark:text-gray-300 mb-2">Vehicle Type</label>
        <div class="grid grid-cols-2 gap-3" id="vehicleTypeDisplay">
          <div id="vt2w" class="rounded-2xl p-3 text-center border-2 border-gray-200 dark:border-dark-600 opacity-40 transition-all">
            <div class="text-2xl mb-1">🛵</div>
            <div class="font-bold text-sm text-gray-600 dark:text-gray-300">2-Wheeler</div>
            <div class="text-xs text-gray-400">Auto-selected</div>
          </div>
          <div id="vt4w" class="rounded-2xl p-3 text-center border-2 border-gray-200 dark:border-dark-600 opacity-40 transition-all">
            <div class="text-2xl mb-1">🚗</div>
            <div class="font-bold text-sm text-gray-600 dark:text-gray-300">4-Wheeler</div>
            <div class="text-xs text-gray-400">Auto-selected</div>
          </div>
        </div>
        <input type="hidden" name="vehicle_type" id="vehicleTypeInput" value="4w"/>
      </div>

      <!-- Vehicle Number -->
      <div class="mb-5">
        <label class="block text-sm font-black text-gray-700 dark:text-gray-300 mb-1.5">
          Vehicle Number *
          <span class="text-xs font-normal text-gray-400 ml-1">Indian format: DL01AB1234</span>
        </label>
        <input type="text" name="vehicle_no" id="vehicleNo" required
               placeholder="e.g. DL01AB1234 or UP32AB1234"
               maxlength="11"
               class="inp uppercase font-mono tracking-widest text-lg"/>
        <p id="vehicleNoError" class="text-red-500 text-xs mt-1 hidden">
          ⚠️ Enter a valid Indian vehicle number (e.g. MH12CD3456)
        </p>
        <p class="text-xs text-gray-400 mt-1">Format: 2 letters + 2 digits + 1-2 letters + 4 digits</p>
      </div>

      <!-- Grace Period Notice -->
      <div class="bg-green-50 dark:bg-green-950/40 border border-green-200 dark:border-green-800 rounded-2xl p-4 mb-6 flex gap-3">
        <span class="text-2xl shrink-0">⏱️</span>
        <div>
          <p class="font-bold text-green-700 dark:text-green-300 text-sm">15-Minute Grace Period</p>
          <p class="text-xs text-green-600 dark:text-green-400 mt-0.5">If you exit within 15 minutes, parking is completely FREE!</p>
        </div>
      </div>

      <button type="submit" id="submitBtn" disabled
        class="btn-primary w-full py-4 rounded-2xl text-base opacity-50 cursor-not-allowed transition-all">
        Select a slot to continue
      </button>
    </form>

    {% else %}
    <div class="text-center py-12">
      <div class="w-16 h-16 rounded-3xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center mx-auto mb-4">
        <i data-lucide="x-circle" class="w-8 h-8 text-red-500"></i>
      </div>
      <p class="text-lg font-bold text-gray-600 dark:text-gray-300">No slots available right now</p>
      <a href="{{ url_for('lots_list') }}" class="btn-primary mt-4 px-8 py-3 rounded-xl inline-flex items-center gap-2">
        Find another lot →
      </a>
    </div>
    {% endif %}
  </div>
</div>
{% endblock %}

{% block scripts %}
<script>
// ── Auto vehicle type from slot selection ────────────────────────────────────
document.querySelectorAll('.slot-radio').forEach(radio => {
  radio.addEventListener('change', function() {
    const type = this.dataset.type;
    document.getElementById('vehicleTypeInput').value = type;

    const vt2w = document.getElementById('vt2w');
    const vt4w = document.getElementById('vt4w');
    const hint = document.getElementById('slotTypeHint');

    if (type === '2w') {
      vt2w.className = vt2w.className.replace('opacity-40','opacity-100').replace('border-gray-200 dark:border-dark-600','border-amber-400 bg-amber-50 dark:bg-amber-900/30 dark:border-amber-500');
      vt4w.className = vt4w.className.replace('opacity-100','opacity-40').replace('border-amber-400 bg-amber-50 dark:bg-amber-900/30 dark:border-amber-500','border-gray-200 dark:border-dark-600');
      hint.textContent = '🛵 2-Wheeler slot selected';
      hint.className = 'ml-2 text-xs font-semibold text-amber-600';
    } else {
      vt4w.className = vt4w.className.replace('opacity-40','opacity-100').replace('border-gray-200 dark:border-dark-600','border-blue-400 bg-blue-50 dark:bg-blue-900/30 dark:border-blue-500');
      vt2w.className = vt2w.className.replace('opacity-100','opacity-40').replace('border-blue-400 bg-blue-50 dark:bg-blue-900/30 dark:border-blue-500','border-gray-200 dark:border-dark-600');
      hint.textContent = '🚗 4-Wheeler slot selected';
      hint.className = 'ml-2 text-xs font-semibold text-blue-600';
    }

    // Enable submit if vehicle number is also filled
    checkFormReady();
  });
});

// ── Vehicle number validation (Indian format) ────────────────────────────────
// Format: XX00XX0000 — e.g. DL01AB1234, MH12CD3456, UP32KA9876
const vehiclePattern = /^[A-Z]{2}[0-9]{2}[A-Z]{1,3}[0-9]{4}$/;

const vehicleInput = document.getElementById('vehicleNo');
vehicleInput.addEventListener('input', function() {
  this.value = this.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
  checkFormReady();
});

vehicleInput.addEventListener('blur', function() {
  const err = document.getElementById('vehicleNoError');
  if (this.value && !vehiclePattern.test(this.value)) {
    err.classList.remove('hidden');
    this.classList.add('border-red-400');
    this.classList.remove('border-green-400');
  } else if (this.value) {
    err.classList.add('hidden');
    this.classList.remove('border-red-400');
    this.classList.add('border-green-400');
  }
});

function checkFormReady() {
  const slotSelected = document.querySelector('.slot-radio:checked');
  const vehicleOk    = vehiclePattern.test(vehicleInput.value);
  const btn          = document.getElementById('submitBtn');
  if (slotSelected && vehicleOk) {
    btn.disabled = false;
    btn.classList.remove('opacity-50','cursor-not-allowed');
    btn.textContent = '✅ Confirm Booking';
  } else {
    btn.disabled = true;
    btn.classList.add('opacity-50','cursor-not-allowed');
    btn.textContent = slotSelected ? 'Enter valid vehicle number' : 'Select a slot to continue';
  }
}

// ── Prevent invalid vehicle number on submit ─────────────────────────────────
document.getElementById('bookForm')?.addEventListener('submit', function(e) {
  if (!vehiclePattern.test(vehicleInput.value)) {
    e.preventDefault();
    document.getElementById('vehicleNoError').classList.remove('hidden');
    vehicleInput.focus();
  }
});
</script>
{% endblock %}
