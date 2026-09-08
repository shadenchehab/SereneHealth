/**
 * Simple PoC site gate (client-side). Change USER / PASS for the customer demo.
 * Not bank-grade — stops casual visitors who land on the link.
 */
(function (global) {
  var GATE_KEY = 'serene-health-poc-gate';
  var USER = 'serene';
  var PASS = 'SerenePoC2026';

  function isAuthed() {
    try {
      return sessionStorage.getItem(GATE_KEY) === '1';
    } catch (e) {
      return false;
    }
  }

  function login(username, password) {
    if (String(username).trim() === USER && String(password) === PASS) {
      try {
        sessionStorage.setItem(GATE_KEY, '1');
      } catch (e) {}
      return true;
    }
    return false;
  }

  function logout() {
    try {
      sessionStorage.removeItem(GATE_KEY);
    } catch (e) {}
  }

  function requireAuth() {
    if (isAuthed()) return;
    var next = encodeURIComponent(location.pathname + location.search + location.hash);
    location.replace('/login.html?next=' + next);
  }

  global.PocGate = {
    USER: USER,
    isAuthed: isAuthed,
    login: login,
    logout: logout,
    requireAuth: requireAuth,
    OTP_URL:
      'https://connectadevrev-otp-board.serenehealth.workers.dev/?k=01a1d5f989af27abaf5e997e918568a2a0d661d1ea1a4484'
  };
})(window);
