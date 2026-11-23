"""Five past events, used by the "Past events" and "Compare" views.

runup  = a month in the build-up, before the damage (the "does today look like the calm before?" check)
worst  = the month India was hit hardest
calm   = roughly when things had settled
Numbers in the key tables are read from the data, not typed here, so they always match the charts.
"""

KEY = ["fed", "fedBs", "us10", "dxy", "brent", "fii", "inr", "rbi", "inCpi", "nifty", "vix", "inVix"]

EVENTS = {
    "dotcom": dict(
        name="2000 · Dot-com crash",
        short="Dot-com",
        runup="2000-02", worst="2001-09", calm="2003-05",
        color="#F472B6",
        trigger="A US tech-stock bubble burst.",
        story=(
            "Through the late 1990s, investors poured money into internet companies with little or no profit. "
            "The Nasdaq peaked in March 2000 and then lost most of its value over the next two and a half years. "
            "India had its own tech mania: IT stocks led the market up and then led it down. A broker-led stock "
            "scam in early 2001 made the fall in Indian markets worse. The US slipped into recession in 2001, and the "
            "September 11 attacks delivered a final shock before markets bottomed. The Fed cut rates aggressively "
            "through 2001 to cushion the economy."
        ),
        chain=[
            ("Moves first", "US tech stocks fall sharply. This time stocks lead, not the Fed."),
            ("Carries the change", "Global investors cut risk everywhere, and foreign money leaves emerging markets."),
            ("Reacts", "Indian IT stocks, the most expensive part of the market, fall the hardest."),
            ("Moves last", "Nifty slides for more than a year. The Fed's rate cuts help only slowly."),
        ],
        lesson="A crash can start in stocks, not in rates. When one sector gets very expensive, India follows the US down in that sector.",
        watch="Very high valuations in one popular theme (then internet, today AI), and the Nasdaq falling while the Fed is still not cutting.",
    ),
    "gfc": dict(
        name="2008 · Global financial crisis",
        short="2008 crisis",
        runup="2007-12", worst="2008-10", calm="2009-05",
        color="#F87171",
        trigger="US housing loans went bad and broke the banking system.",
        story=(
            "US banks had made and repackaged huge amounts of risky home loans. When house prices fell, those loans "
            "went bad and banks stopped trusting each other. Lehman Brothers collapsed in September 2008, and "
            "lending froze around the world. Everyone scrambled for dollars, so the dollar jumped even though the crisis "
            "started in the US. Foreign investors pulled money out of India, the rupee fell sharply and the Nifty lost "
            "more than half its value from its January 2008 peak. Oil had spiked to a record in mid-2008, then "
            "collapsed. The Fed cut to near zero and started buying bonds (QE). The RBI cut rates hard and released "
            "cash into banks."
        ),
        chain=[
            ("Moves first", "US housing and bank losses, then the Lehman collapse. The Fed cuts to zero and starts QE."),
            ("Carries the change", "A rush for dollars: the dollar rises and foreign investors sell Indian stocks heavily."),
            ("Reacts", "The rupee weakens a lot, the RBI sells dollars and then cuts rates fast."),
            ("Moves last", "Nifty falls more than 50% from its peak. VIX hits record highs."),
        ],
        lesson="In a real panic, money runs to the dollar, even if the US caused the problem. India's markets get hit through foreign selling, not its own economy.",
        watch="Stress in US banks or credit, VIX above 40, the dollar rising while US stocks fall.",
    ),
    "taper": dict(
        name="2013 · Taper tantrum",
        short="Taper tantrum",
        runup="2013-04", worst="2013-08", calm="2014-03",
        color="#A78BFA",
        trigger="The Fed only hinted it would slow its bond buying.",
        story=(
            "In May 2013, the Fed chair said the Fed might start slowing its bond buying (QE). Nothing actually changed "
            "yet, but US 10-year yields jumped quickly. Money that had flowed into emerging markets looking for "
            "higher returns rushed back to the US. India was among the worst hit because it was running a very large "
            "current account deficit and high inflation, so it needed foreign money every month. Analysts grouped it "
            "with four others as the 'Fragile Five'. The rupee hit a record low in late August. The RBI tightened "
            "cash in the banking system, curbed gold imports and, under a new governor from September, raised "
            "dollar deposits from Indians abroad, which calmed the rupee."
        ),
        chain=[
            ("Moves first", "A Fed signal about slowing QE. No rate change at all."),
            ("Carries the change", "US 10Y yields jump, the gap with India narrows and foreign bond and stock money leaves."),
            ("Reacts", "The rupee falls to a record low. The RBI defends it with tight liquidity and special measures."),
            ("Moves last", "Bank Nifty and rate-sensitive stocks fall most, while exporters and IT do better."),
        ],
        lesson="Words from the Fed can hit India as hard as actions. A big current account deficit is what makes India vulnerable.",
        watch="US 10Y yields rising fast, India's current account deficit widening above about 2.5% of GDP, the India–US yield gap shrinking.",
    ),
    "covid": dict(
        name="2020 · COVID crash",
        short="COVID",
        runup="2020-01", worst="2020-03", calm="2020-11",
        color="#FBBF24",
        trigger="A pandemic shut down the world economy almost overnight.",
        story=(
            "As COVID spread in early 2020, countries locked down and business activity stopped. Markets fell faster "
            "than in any earlier crash, and fear gauges (VIX, India VIX) hit record levels in March. Foreign investors "
            "sold record amounts of Indian stocks that month, the rupee weakened and oil prices collapsed as demand "
            "vanished. The Fed cut to zero and launched unlimited bond buying, almost doubling its balance sheet within "
            "months. The RBI cut rates twice and flooded banks with cash. That wall of money turned markets around "
            "quickly, and by late 2020 foreign money was pouring back into India."
        ),
        chain=[
            ("Moves first", "A shock outside finance. The Fed responds within days with zero rates and huge QE."),
            ("Carries the change", "Panic selling, then a flood of new dollars. Foreign money leaves, then returns in record amounts."),
            ("Reacts", "The rupee dips, the RBI cuts rates and adds liquidity, and oil crashes, which helps India."),
            ("Moves last", "Nifty falls almost 40% in weeks, then recovers within about a year."),
        ],
        lesson="When the Fed and RBI respond with massive support, a crash can reverse quickly. Fast, big policy support matters more than the size of the fall.",
        watch="A sudden spike in VIX together with the Fed balance sheet starting to grow again.",
    ),
    "hikes2022": dict(
        name="2022 · Inflation and rate hikes",
        short="2022 hikes",
        runup="2021-12", worst="2022-06", calm="2022-12",
        color="#2DD4BF",
        trigger="Inflation surged, and the Fed raised rates at the fastest pace in decades.",
        story=(
            "After the pandemic, demand came back faster than supply and inflation climbed. Russia's invasion of "
            "Ukraine in February 2022 pushed oil and food prices higher still. The Fed started hiking in March 2022 and "
            "kept going in big steps, and from June it also began shrinking its balance sheet (QT). The dollar rose to "
            "a 20-year high. Foreign investors sold Indian stocks month after month, the rupee crossed 80 for the "
            "first time, and the RBI made a surprise rate hike in May and kept raising rates through the year. "
            "Strong buying by Indian mutual funds and SIPs limited the fall in the Nifty."
        ),
        chain=[
            ("Moves first", "Hot US inflation and jobs data. The Fed hikes fast and starts QT. Oil spikes."),
            ("Carries the change", "US yields and the dollar rise strongly. Foreign investors sell for months."),
            ("Reacts", "The rupee hits new lows, India's inflation rises above 7%, and the RBI hikes rates repeatedly."),
            ("Moves last", "Nifty falls about 15–18%, a much smaller fall than in earlier crises, because domestic investors keep buying."),
        ],
        lesson="Inflation-driven hikes hit India through oil, the dollar and foreign selling. Domestic buying is now a big cushion.",
        watch="US CPI staying high, the Fed hiking or shrinking its balance sheet, Brent rising, India CPI above 6%.",
    ),
}
