var shots = require('./screenshots');

function option(value, index, name, text) {
  return {
    label: '<img src="' + shots[index] + '" alt="" ' +
      'style="display:block;width:130px;height:130px;margin:4px 0 8px">' +
      '<strong>' + name + '</strong> – ' + text,
    value: value
  };
}

module.exports = [
  {
    "type": "heading",
    "defaultValue": "WKC Kneipenchor"
  },
  {
    "type": "text",
    "defaultValue": "Außenring = Minuten, Innenring = Stunden."
  },
  {
    "type": "section",
    "items": [
      {
        "type": "heading",
        "defaultValue": "Design"
      },
      {
        "type": "radiogroup",
        "messageKey": "STYLE",
        "label": "Zifferblatt",
        "defaultValue": "0",
        "options": [
          option("0", 0, "Pegel", "die Ringe füllen sich"),
          option("1", 1, "Lücke", "Kronkorken in der Ringlücke"),
          option("2", 2, "Prost", "glatte Bögen")
        ]
      },
      {
        "type": "toggle",
        "messageKey": "BATTERY",
        "label": "Akkustand als Bier in der Flasche",
        "defaultValue": true
      }
    ]
  },
  {
    "type": "submit",
    "defaultValue": "Speichern"
  }
];
