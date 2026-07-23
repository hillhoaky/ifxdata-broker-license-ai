# License type standardization

Use this reference before changing an IFXData broker license `type`. The goal is consistent dropdown values across brokers.

## Selection rules

1. Read the current English dropdown list with `GET /broker/getAllLicenseType?language=en&pageSize=500&pageNum=1`.
2. Prefer an exact official-meaning match from existing IFXData types.
3. If multiple types are close, choose the one matching the official licence wording/scope, not the broker's marketing wording.
4. Do not invent free-form text in broker `updateLicense.type`.
5. If no close type exists and the user has authorized type maintenance, create a new English type through `addLicenseType` using:
   - `name`: dropdown name / entered license name
   - `licenseType`: same as `name` unless IFXData convention requires a shorter label
   - `typeRange`: English scope/range text, concise
   - `note`: English introduction/description, concise
   - `language`: `en`
   - `color`: `Black`
6. Verify the new type appears in `getAllLicenseType` before using it on any broker license.

## Standard mapping table

| Regulator / scenario | Official wording or clue | IFXData type to use | Notes |
|---|---|---|---|
| South Africa FSCA | Financial Services Provider, Category I FSP, advice/intermediary services | `Financial Services Provider` | Use for ordinary FSP licences. |
| South Africa FSCA | OTC derivatives / ODP authorisation | `Financial derivatives` unless `OTC Derivative Provider` exists | If ODP appears frequently, create `OTC Derivative Provider`. |
| South Africa FSCA | Crypto Assets sub-category / CASP | `Virtual asset service provider` | Use when the licence is specifically virtual-asset related. |
| Mauritius FSC | Investment Dealer, Full Service Dealer, Broker | `Investment Dealer` | Do not use Seychelles-style `Securities Dealer Licence` for Mauritius unless official wording says so. |
| Seychelles FSA | Securities Dealer Licence | `Securities Dealer Licence` | Standard for Seychelles FSA broker licences. |
| Vanuatu VFSC | Financial Dealers License / Licence | `Financial Dealers License` | If class A/B/C/D is explicit and a matching subtype exists later, use the subtype. |
| Hong Kong SFC | Type 1 / Dealing in securities | `Dealing in securities(Type 1)` | Securities dealing. |
| Hong Kong SFC | Type 2 / Dealing in futures contracts | `Dealing in Futures Contracts(Type 2))` | Keep IFXData spelling even with the extra parenthesis. |
| Hong Kong SFC | Type 4 / Advising on securities | `Advising on securities(Type 4)` | Securities advice/research. |
| Hong Kong SFC | Type 5 / Advising on futures contracts | `Advising on futures contracts(Type 5)` | Futures advice/research. |
| Singapore MAS | Capital Markets Services Licence | `Capital Markets Services License` | Use for CMS permissions. |
| Japan FSA | Type I Financial Instruments Business | `Type I Financial Instruments Business` | Use for Type I FIBO licences. |
| Cayman CIMA | Securities Investment Business Licence / SIBL | `SIBL License` | Use the corrected IFXData dropdown value for Cayman Securities Investment Business Licence records. |
| UAE SCA | Category 5, financial consultation, promotion, introduction | `Category 5 License` | Not a full trading/execution licence. |
| UAE SCA | Category 1 | `Category 1 License` | Use only when official category is clearly Category 1. |
| Dubai DFSA | Category 3A brokerage permissions | `Category 3A License` | Use for DFSA Category 3A when disclosed. |
| United States FinCEN | MSB registration | `Money Services Business` | This is registration/AML compliance, not forex/securities/CFD authorization. |
| New Zealand FSPR or similar registry | Financial Service Provider Registration / FSP registration | `Financial Service Provider Registration` | Use for registry-based financial service provider status; it is not automatically a full trading, securities, forex, or derivatives licence. |
| Virtual asset / crypto | VASP, crypto exchange registration, virtual asset service provider | `Virtual asset service provider` | Use for crypto/virtual-asset registration. |
| United Kingdom Companies House or similar | Company registration only | `Business Registration` | Not a financial regulatory licence. |
| Generic non-financial company registry | Commercial/company registration | `Common Business Registration` | Use when it is clearly not financial authorization. |
| Official warning | Clone firm | `Clone Firm` | Use for confirmed clone-risk records. |
| Invalid/fake licence | Illegal, false, no legal basis | `Illegal license` | Use only with strong evidence or user confirmation. |
| Cannot verify | Unknown or insufficient evidence | `Unverified` | Use when not clearly invalid. |

## Existing IFXData types useful for high-frequency regulators

- `Market Maker (MM)`: official permission indicates dealing as principal / market making.
- `Straight Through Processing (STP)`: order routing / agency execution / STP style.
- `Retail Forex License`: retail forex/CFD licence where MM/STP is not clearly stated.
- `Investment Advisory License`: advice/research only, no trading execution.
- `Appointed Representative(AR)`: representative status under another authorised firm.
- `European Authorized Representative (EEA)`: EEA passporting/representative status.
- `Financial Service Provider Registration`: registry-based FSP status, such as New Zealand FSPR-style records; weaker than a full financial trading licence.
- `Financial Service Corporate`, `Financial Service`, `Common Financial Service License`: fallback only when a regulator's exact type is missing and no better existing option fits.

## New type candidates

Create only when needed and user-authorized. Suggested English definitions:

### OTC Derivative Provider

- `name`: `OTC Derivative Provider`
- `licenseType`: `OTC Derivative Provider`
- `typeRange`: `Authorises an entity to act as a counterparty or provider for over-the-counter derivative products, subject to the regulator's approved conditions.`
- `note`: `An OTC Derivative Provider authorisation allows regulated OTC derivatives business. It is commonly relevant to CFDs and other derivative products.`
- `color`: `Black`

### Category I Financial Services Provider

- `name`: `Category I Financial Services Provider`
- `licenseType`: `Category I Financial Services Provider`
- `typeRange`: `Covers approved advice and intermediary services for financial products under the regulator's authorised product categories.`
- `note`: `A Category I FSP licence allows a firm to provide approved financial advice and intermediary services, but it is not automatically a full CFD or market-making licence.`
- `color`: `Black`

## Existing user-created type

### Financial Service Provider Registration

- IFXData ID at creation time: `2198`
- `name`: `Financial Service Provider Registration`
- `licenseType`: `Financial Service Provider Registration`
- `typeRange`: `Applies to financial service provider registrations, including registry-based authorisation or disclosure status. It may cover financial-service activities only within the limits shown by the relevant registry or regulator.`
- `note`: `A Financial Service Provider Registration confirms that a firm is listed as a financial service provider, but it is usually a registration status rather than a full trading or derivatives licence.`
- `color`: `Black`
