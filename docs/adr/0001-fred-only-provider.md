# FRED is the only data provider in v1

FRED already serves nearly the whole v1 indicator universe via one API and one key (the live list is the SERIES map in the FRED fetcher). ISM, MOVE, and CCC spreads are licensed and unavailable on free sources anyway, so a provider abstraction would be built for sources we mostly cannot use. We build directly against FRED and add a provider layer only when a second real provider arrives.
