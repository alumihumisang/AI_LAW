# XRAG Experiment Line Naming

This file defines the stable naming scheme for the 18 XRAG generation-evaluation lines.

## Tau Levels

- `L` = `tau = 0.075`
- `M` = `tau = 0.100`
- `H` = `tau = 0.125`

## Weight Codes

- `FI` = `Fact=0.5, Injury=0.3, Compensation=0.2`
- `FC` = `Fact=0.5, Injury=0.2, Compensation=0.3`
- `IF` = `Fact=0.3, Injury=0.5, Compensation=0.2`
- `CF` = `Fact=0.3, Injury=0.2, Compensation=0.5`
- `IC` = `Fact=0.2, Injury=0.5, Compensation=0.3`
- `CI` = `Fact=0.2, Injury=0.3, Compensation=0.5`

The two-letter code is ordered by dominant weight priority:

- `FI` means `Fact > Injury > Compensation`
- `FC` means `Fact > Compensation > Injury`
- `IF` means `Injury > Fact > Compensation`
- `CF` means `Compensation > Fact > Injury`
- `IC` means `Injury > Compensation > Fact`
- `CI` means `Compensation > Injury > Fact`

## Stable 18-Line Mapping

| Exp ID | Short Name | Full Setting |
|---|---|---|
| E01 | FI-L | Fact=0.5, Injury=0.3, Compensation=0.2, tau=0.075 |
| E02 | FC-L | Fact=0.5, Injury=0.2, Compensation=0.3, tau=0.075 |
| E03 | IF-L | Fact=0.3, Injury=0.5, Compensation=0.2, tau=0.075 |
| E04 | CF-L | Fact=0.3, Injury=0.2, Compensation=0.5, tau=0.075 |
| E05 | IC-L | Fact=0.2, Injury=0.5, Compensation=0.3, tau=0.075 |
| E06 | CI-L | Fact=0.2, Injury=0.3, Compensation=0.5, tau=0.075 |
| E07 | FI-M | Fact=0.5, Injury=0.3, Compensation=0.2, tau=0.100 |
| E08 | FC-M | Fact=0.5, Injury=0.2, Compensation=0.3, tau=0.100 |
| E09 | IF-M | Fact=0.3, Injury=0.5, Compensation=0.2, tau=0.100 |
| E10 | CF-M | Fact=0.3, Injury=0.2, Compensation=0.5, tau=0.100 |
| E11 | IC-M | Fact=0.2, Injury=0.5, Compensation=0.3, tau=0.100 |
| E12 | CI-M | Fact=0.2, Injury=0.3, Compensation=0.5, tau=0.100 |
| E13 | FI-H | Fact=0.5, Injury=0.3, Compensation=0.2, tau=0.125 |
| E14 | FC-H | Fact=0.5, Injury=0.2, Compensation=0.3, tau=0.125 |
| E15 | IF-H | Fact=0.3, Injury=0.5, Compensation=0.2, tau=0.125 |
| E16 | CF-H | Fact=0.3, Injury=0.2, Compensation=0.5, tau=0.125 |
| E17 | IC-H | Fact=0.2, Injury=0.5, Compensation=0.3, tau=0.125 |
| E18 | CI-H | Fact=0.2, Injury=0.3, Compensation=0.5, tau=0.125 |

## Recommended Plot Labels

Use these short labels in figure legends:

- `FI-L`
- `FI-M`
- `FI-H`
- `FC-L`
- `FC-M`
- `FC-H`
- `IF-L`
- `IF-M`
- `IF-H`
- `CF-L`
- `CF-M`
- `CF-H`
- `IC-L`
- `IC-M`
- `IC-H`
- `CI-L`
- `CI-M`
- `CI-H`

## Recommended Baseline Labels

- `RAG-Baseline`
- `CAG`

## Thesis Wording

Recommended wording for the paper:

`The 18 XRAG variants are named using a compact code of the form XY-Z, where XY denotes the weight-priority order among Fact, Injury, and Compensation, and Z denotes the tau level (L, M, H). For example, FI-L represents Fact=0.5, Injury=0.3, Compensation=0.2 under the low tau setting.`
