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
          { "label": "Pegel – die Ringe füllen sich", "value": "0" },
          { "label": "Lücke – Kronkorken in der Ringlücke", "value": "1" },
          { "label": "Prost – glatte Bögen", "value": "2" }
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
