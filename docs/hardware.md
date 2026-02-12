```mermaid
flowchart LR

  %% --- POWER ---
  subgraph Power["Power (AC/DC)"]
    UPS["UPS"]
    PS["Power Station(s)"]
  end

  UPS -->|AC power| ES["Ethernet Switch"]
  UPS -->|AC power| MS["Monitor Switch (5W)"]
  UPS -->|AC power| M1["Monitor 1"]
  UPS -->|AC power| M2["Monitor 2"]
  UPS -->|AC power| PS

  PS -->|Micro USB power| RPI["Raspberry Pi (30W)"]
  PS -->|USB-C power| LAP["Laptop (65W)"]
  PS -->|USB-C power| DOCK["Laptop Dock (unknown)"]
  PS -->|USB-A charge only| MOUSE["Corsair Mouse (battery)"]

  %% --- VIDEO / USB (KVM) ---
  subgraph KVM["Video + USB Switching"]
    MS
    CAM["Camera"]
    KBD["Corsair Keyboard (2W)"]
    DONG["Mouse Dongle"]
  end

  %% Laptop dock -> monitor switch (PC1)
  DOCK -->|HDMI PC1| MS
  DOCK -->|HDMI PC1| MS
  DOCK -->|USB-A 3.0 PC1| MS

  %% Raspberry Pi -> monitor switch (PC2)
  RPI -->|HDMI PC2| MS
  RPI -->|HDMI PC2| MS
  RPI -->|USB-A 3.0 PC2| MS

  %% Outputs from monitor switch
  MS -->|USB-A 3.0| CAM
  MS -->|USB-A 3.0| DONG
  MS -->|USB-A 3.0| KBD

  %% Laptop <-> Dock comms
  LAP <-->|USB-C comms| DOCK

  %% --- NETWORK ---
  subgraph Network["Network (RJ45)"]
    ES
    NAS["NAS"]
    NET["Internet"]
  end

  LAP -->|RJ45| ES
  RPI -->|RJ45| ES
  NAS -->|RJ45| ES
  NET -->|RJ45| ES
```

# Bill of Materials


| Qnty | Description | Unit | Price |
|------|-------------|------|-------|
|   2  | [WD Red Plus 10TB NAS Drive](https://www.amazon.co.uk/dp/B0FPDHLHML/?coliid=I2X71PO10MR97X&colid=VW7CRXVOSJBD)       | 220 | 440  |
|   1  | [SYNOLOGY 4-Bay DS925+ NAS](https://www.amazon.co.uk/dp/B0C8S7SF4B/?coliid=I8NKTNDONUBGG&colid=VW7CRXVOSJBD)         | 565 | 565  |
|   4  | [Ethernet Cable 1M](https://www.amazon.co.uk/dp/B0DB4M1KVY/?coliid=I3R2JN2H72GK8F&colid=VW7CRXVOSJBD)                | 8   | 32   |
|   1  | [SODOLA 5 Port 10Gb Switch](https://www.amazon.co.uk/dp/B0FNQZ63S5/?coliid=I1K6XXIBKS51V8&colid=VW7CRXVOSJBD)        | 160 | 160  |
|   1  | [800W USB C Charging](https://www.amazon.co.uk/Charging-Station-10%E2%80%91Port-Multiport-Compatible/dp/B0FKMGC4Q7/) | 50  | 50   |
|   1  | [Docking Station](https://www.amazon.co.uk/gp/product/B0BDDW8P9Q/?th=1)                                              | 187 | 187  |
|   1  | [900W UPS](https://www.amazon.co.uk/SKE-Battery-Protector-Computer-Uninterruptible/dp/B0CKW2RS7W)                    | 140 | 140  |