# Cellgate Home Assistant Integration

Custom Home Assistant integration for [Cellgate](https://cell-gate.com/) gate access control systems.

## Features

- Automatic discovery of all gates and doors on your account
- Button entities for momentary gate open
- Supports multiple communities, devices, and ports which are pulled from your account the same way as the mobile app

## Installation

### HACS (recommended)

1. Add this repository as a custom repository in HACS
2. Install "Cellgate"
3. Restart Home Assistant

### Manual

Copy `custom_components/cellgate/` to your Home Assistant `config/custom_components/` directory.

## Setup

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for "Cellgate"
3. Enter your Cellgate account email and password
4. Your gates will be automatically discovered and added as button entities



## Notes

There is login failure logic for this integration to avoid spamming failed logins and potential lockouts. I don't think Cellgate actually has lockout logic but it's there just in case.

The API uses two different HTTP request patterns: one using a body and another using headers. It's strange.

The Android app was reversed to determine the HTTP calls and login flow. It interestingly uses Linphone for the SIP calls. I don't have any plan to add SIP support to this integration.