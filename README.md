# Waltr for Home Assistant

Unofficial Home Assistant integration for [Waltr](https://waltr.in) smart water tank systems. It uses the
[Waltr API](https://api.waltr.in/docs/api/) and needs a Waltr API token.

## What you get

Every Waltr device shows up as its own Home Assistant device.

| Waltr device | Entities |
|---|---|
| Tank (Waltr A) | Water level %, water volume, capacity, TDS (when the tank has the sensor), inflow / outflow / tanker water today, battery, online, last updated |
| Motor (Waltr C) | Pump switch, run time, status, running, fault, online, energy today (three-phase only), last command by |
| Borewell (Waltr B) | Pump switch, run time, schedule switch, status, running, fault, online, energy today (three-phase only), last command by |
| Valve (Waltr V) | Valve (open / close), status, fault, battery, online |

The pump, valve and schedule controls need a **Waltr Premium** plan. Without one, the readings still work and the
controls show an error when you use them.

### How the controls behave

- **Pump switch:** for timer-based motors and borewells, turning it on runs the pump for the **Run time** setting
  (default 30 minutes), and the controller stops it after that. Event-based motors simply turn on or off.
- **Waltr's safety rules still apply.** If a tank is full, offline or too low, Waltr refuses to start the pump and
  Home Assistant shows the reason.
- **Valves** can take up to 5 minutes to open or close.

### Updates

The integration checks Waltr every minute, and fetches today's totals every 15 minutes. Waltr's API allows
5 requests per second; the integration spaces its requests to stay under that.

## Install with HACS

1. In Home Assistant, open **HACS**.
2. Click the **⋮** menu at the top right and choose **Custom repositories**.
3. Enter `https://github.com/rkarthikn/ha-waltr`, choose the type **Integration**, and click **Add**.
4. Search HACS for **Waltr**, open it, and click **Download**.
5. Restart Home Assistant from **Settings → System → Restart**.
6. Go to **Settings → Devices & services → Add integration**, search for **Waltr**, and paste your API token.

## Install by hand

Copy `custom_components/waltr` into your Home Assistant `config/custom_components/` folder, restart, and add the
integration as in step 6.

## Disclaimer

This project isn't made or supported by Waltr.
