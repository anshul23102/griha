# Third-party data: what we may and may not do

Last checked 2026-11-10 by reading the primary documents. This is a working summary by the project, not legal advice.

## Freddie Mac Single-Family Loan-Level Dataset
Source: Freddie Mac, *Terms and Conditions for the Single-Family Loan-Level Dataset*, Freddie Mac website version effective November 2025 (last updated 3 Nov 2025). Dataset page: <https://freddiemac.com/research/datasets/sf-loanlevel-dataset>.

| The terms say | What we do |
|---|---|
| Use is for personal or internal purposes of analysing or researching the credit performance of the mortgages | Local analysis only, on the developer's own machine |
| The data may not be modified beyond what that purpose needs | Read-only; we only select columns and compute metrics |
| Derived data and "Derived Products" may be created for the Internal Purpose and shared only inside your organisation | A model trained on the data would be a Derived Product, so **the shipped model is never trained on it** |
| Academic or research results may be made public if solely non-commercial and they cannot recreate the data or identify anyone | Only aggregate figures (counts, AUC, calibration by decile); nothing at loan level. Held back until Freddie Mac confirms in writing that a student competition entry is acceptable, because a prize-bearing contest may not count as non-commercial |
| No giving or posting the data, in whole or part, or Derived Products to third parties | Data lives in `data-external/` (not committed, not deployed, excluded by `ops/deploy-vm.sh` and `.dockerignore`); the public site and repository never contain it |
| No linking to identify individuals | Loan IDs are never joined to anything |
| A link to the dataset page is allowed under their Linking Policy | The Data sources page links to it |

Questions go to Freddie Mac (the terms list `SF_Loan_Level_Data_Inquiry@freddiemac.com`; the dataset page also lists `clarity@freddiemac.com`).

### Draft email
> Subject: Question on permitted use of the Single-Family Loan-Level Dataset in a student competition
>
> Hello,
>
> I am a student registered for the Clarity Single-Family Loan-Level Dataset and I have read the Terms and Conditions (November 2025 version). I am building an open mortgage-underwriting prototype for a student hackathon (i-Hack, IIT Bombay E-Summit 2026). I would like to score a sample of the data locally with a model that was trained on synthetic data, and report only aggregate validation figures (for example AUC and calibration by decile), clearly labelled as US data, with a citation to Freddie Mac. No loan-level data or Derived Product would be shared, and the model would not be trained on the dataset.
>
> Would publishing those aggregate results in the competition submission fall within the terms for academic or research, non-commercial use? The competition awards prizes, so I would like to confirm before publishing anything.
>
> Thank you,
> [name]

## openICPSR project 116500 (India mortgages)
<https://www.openicpsr.org/openicpsr/project/116500/version/V1/view> contains only code and a licence file. The data is not included. Not used.

## Indian public figures used in the product
- RBI repo rate: public RBI publication, cited with link and date on the Data sources page.
- NHB RESIDEX: public NHB press release, cited with link, quarter and publication date. We state the figures and attribute them; we do not republish the release.

## Rule for any future dataset
Read its terms first. If we cannot say what we may do with it and what we may publish, we do not use it.
