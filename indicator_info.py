"""Detailed text for every indicator page.

what   = what it is, in plain words
source = who publishes it and when
read   = how to read the number (normal / hot / worrying)
path   = how a move travels to India, step by step
watch  = what to look for in it
"""

INFO = {
    "usJobs": dict(
        what="The number of jobs US employers added (or cut) in the month, from the 'non-farm payrolls' report. "
             "It is the single most watched US data release because it shows whether the economy is hiring or slowing.",
        source="US Bureau of Labor Statistics, usually on the first Friday of the next month. The two earlier months are revised each time.",
        read="About +100k to +200k a month is healthy and normal. Above +250k is 'hot' and pushes the Fed toward higher rates. "
             "Near zero or negative suggests a slowdown and makes rate cuts more likely. Note the April 2020 crash of about −20 million jobs.",
        path="Strong jobs → markets expect the Fed to keep rates high → US 10Y yield and dollar rise → FIIs prefer the US → "
             "FII selling in India → rupee weakens → Nifty under pressure. Weak jobs work the other way, unless they signal a recession.",
        watch="Three months in a row above +250k (a hot run), or a sudden drop below zero. Also watch the revisions to earlier months.",
    ),
    "usCpi": dict(
        what="How much prices of everyday goods and services in the US rose compared with a year ago (Consumer Price Index, year on year). "
             "It is the main inflation number the Fed fights.",
        source="US Bureau of Labor Statistics, around the 10th–15th of the next month.",
        read="The Fed aims for about 2%. Up to 2.5% is comfortable. 3–4% means the Fed stays cautious. Above 4% means the Fed is likely to hike. "
             "It peaked near 9% in mid-2022.",
        path="Hot CPI → Fed holds or hikes → US yields and dollar rise → FII outflows from India → weaker rupee → "
             "imported inflation for India → RBI less able to cut.",
        watch="Whether it is falling toward 2% or getting stuck above 3%. Each release can move markets the same day.",
    ),
    "pmi": dict(
        what="A monthly survey of US factory purchasing managers (ISM Manufacturing PMI). It asks if orders, output, hiring and deliveries are rising or falling. "
             "It is one of the earliest signals of where the economy is heading.",
        source="Institute for Supply Management, on the first business day of the next month. Filled in by hand in data/manual/pmi.csv.",
        read="Above 50 = factories are growing. Below 50 = shrinking. Below 45 is a recession warning. Above 55 is strong growth.",
        path="Strong PMI → stronger US growth → higher yields and dollar, but also more demand for Indian exports. "
             "Very weak PMI → recession fears → global risk-off → FII selling in India.",
        watch="A move across 50 in either direction, and the 'prices paid' part of the survey, which hints at future inflation.",
    ),
    "gdp": dict(
        what="How fast the US economy grew in the quarter, shown as an annual rate (real GDP, adjusted for inflation).",
        source="US Bureau of Economic Analysis, about a month after each quarter ends, then revised twice.",
        read="About 2% is normal growth. Above 3% is strong. Two negative quarters in a row are a common sign of recession.",
        path="Strong growth supports global demand and Indian exports, but can keep the Fed tight. A US recession usually means "
             "global risk-off, FII selling and falling Indian stocks at first, followed by Fed cuts that help later.",
        watch="A negative quarter, or growth slowing sharply while inflation stays high (stagflation).",
    ),
    "fed": dict(
        what="The interest rate US banks charge each other overnight (effective federal funds rate). The Fed sets a target range for it, "
             "and it is the base for almost every other US interest rate.",
        source="Federal Reserve. The FOMC meets 8 times a year. The daily rate comes from the New York Fed.",
        read="0–0.25% = emergency support (2009–15, 2020–22). 2–3% is roughly neutral. Above 4% is tight. Watch the direction more than the level.",
        path="Higher Fed rate → US deposits and bonds pay more → global money moves to the US → dollar up → FII outflows from India → "
             "rupee weakens → RBI must keep its own rates high to defend the rupee.",
        watch="The start of a hiking or cutting cycle is the biggest signal. The 'dot plot' and press conference show where it may go next.",
    ),
    "fedBs": dict(
        what="The total assets the Fed holds, mostly US government bonds and mortgage bonds. When the Fed buys bonds (QE) it creates new dollars; "
             "when it lets them run off (QT) dollars are removed.",
        source="Federal Reserve weekly H.4.1 report (series WALCL), every Thursday.",
        read="Rising = QE, more dollar liquidity worldwide. Falling = QT, liquidity drained. It went from about $0.9T before 2008 to about $9T in 2022.",
        path="QE → more dollars chasing returns → money flows into emerging markets like India → FII buying, stronger rupee, higher Nifty. "
             "QT → the opposite, slowly.",
        watch="A turn from shrinking to growing (or the reverse). Also watch the pace: fast QT drains liquidity faster.",
    ),
    "brent": dict(
        what="The global benchmark price of crude oil, in US dollars per barrel.",
        source="Daily market price (FRED series DCOILBRENTEU, from the US EIA).",
        read="Around $60–80 is comfortable for India. Above $90 starts to hurt. Above $110 is a serious shock. India imports about 85% of its oil.",
        path="Oil up → India's import bill rises → current account deficit widens → more dollars needed → rupee weakens → "
             "fuel and transport costs feed into India CPI → RBI less able to cut → pressure on Nifty, especially oil-using sectors.",
        watch="A spike of more than about 20% in three months, and whether it comes with a war or supply shock.",
    ),
    "us10": dict(
        what="The yield (interest rate) on 10-year US government bonds. It is the world's main 'risk-free' long-term rate, "
             "and it reflects where markets think the Fed and inflation are heading.",
        source="US Treasury market, daily (FRED series DGS10).",
        read="Below 2% = very easy money. 3–4% is normal for today. Above 4.5% starts to pull money away from riskier assets. Speed matters: a 1% jump in a few months is a shock.",
        path="Higher US 10Y → safe US bonds look more attractive → the India–US gap narrows → FIIs sell Indian bonds and stocks → "
             "rupee weakens → Indian bond yields rise too → banks and rate-sensitive stocks fall.",
        watch="Fast rises like 2013 and 2022. Also watch for big moves on Fed or CPI days.",
    ),
    "gap": dict(
        what="Indian 10-year government bond yield minus the US 10-year yield. It shows how much extra return a foreign investor gets for holding Indian bonds.",
        source="Calculated here from the OECD India long-term rate and the US 10Y (FRED).",
        read="Historically about 4–7 points. Below about 3 points makes India less attractive for foreign bond money, especially once you count the risk of the rupee falling.",
        path="Wider gap → foreign bond money comes in → rupee supported → lower borrowing costs. Narrow gap → foreign money leaves → rupee weakens.",
        watch="The gap shrinking quickly because US yields are rising, as in 2013 and 2022.",
    ),
    "dxy": dict(
        what="The US dollar index, which measures the dollar against six major currencies (mostly the euro, plus yen, pound, Canadian dollar, Swedish krona, Swiss franc).",
        source="ICE futures market, daily (Yahoo symbol DX-Y.NYB).",
        read="Around 90–100 is normal. Above 105 is a strong dollar, which is tough for emerging markets. It hit about 114 in 2022.",
        path="Strong dollar → global money prefers US assets → emerging-market currencies fall, including the rupee → "
             "FII selling in India → RBI sells dollars from reserves → less rupee cash in banks → tighter liquidity → Bank Nifty under pressure.",
        watch="A rise of more than about 5% in three months. In panics the dollar rises even when the US is the problem (2008, 2020).",
    ),
    "usRes": dict(
        what="Cash that US banks keep at the Fed (reserve balances). It is a direct measure of how much dollar liquidity is in the banking system.",
        source="Federal Reserve H.4.1 weekly report (series WRESBAL).",
        read="It moves with QE and QT, and also with the US Treasury's cash account and tax dates. Falling fast = dollar liquidity is getting tight.",
        path="Reserves fall → dollar funding gets tighter → dollar strengthens → FIIs cut risk in places like India → rupee and Nifty under pressure.",
        watch="Sharp drops around tax dates or big Treasury borrowing, and the low points that forced the Fed to act in 2019.",
    ),
    "fii": dict(
        what="Net buying or selling of Indian shares by foreign institutional investors (also called FPIs) in the cash market during the month.",
        source="NSE provisional daily data, summed by month (via tapetide.com). Filled in data/manual/flows.csv. Available from Jan 2014.",
        read="Positive = foreigners are buying, negative = selling. ₹±10,000 crore in a month is a normal swing. Selling above ₹40,000 crore in a month is heavy. "
             "October 2024 and March 2026 saw selling of more than ₹1 lakh crore.",
        path="FII selling → they convert rupees to dollars → rupee weakens → index heavyweights (banks, large caps) fall. "
             "Strong domestic (DII) buying, mostly mutual funds and SIPs, now often absorbs this.",
        watch="Several months of selling in a row, and whether DII buying is large enough to cover it.",
    ),
    "inr": dict(
        what="How many rupees one US dollar buys. A higher number means a weaker rupee.",
        source="Daily reference rate (FRED series DEXINUS, from the Federal Reserve). The RBI also publishes its own reference rate.",
        read="Over the long run the rupee weakens about 2–4% a year, roughly the inflation gap with the US. A fall of more than 5% in three months is a shock. "
             "It moved from about 40 in early 2008 to above 90 in 2026.",
        path="Weaker rupee → imports (oil, electronics) cost more → India's inflation rises → RBI cannot cut, or must hike. "
             "Exporters (IT, pharma) gain. The RBI often sells dollars to slow a fall.",
        watch="Fast falls, and how much forex the RBI is using to defend the rupee.",
    ),
    "rbi": dict(
        what="The repo rate: the interest rate at which the RBI lends to banks overnight. It is India's main policy rate and sets the base for loan and deposit rates.",
        source="Reserve Bank of India Monetary Policy Committee, 6 meetings a year. Filled in data/manual/rbi.csv.",
        read="It was 4% in 2020–22 (very easy), 6.5% in 2023–24 (tight) and 5.5% after the October 2026 hike. "
             "It is usually set above inflation so that real rates stay positive.",
        path="Higher repo → loans cost more → slower credit growth and demand → lower inflation over time. It also supports the rupee by keeping Indian yields attractive. "
             "Rate cuts help banks, real estate, autos and the Nifty.",
        watch="A change in stance (for example neutral to tightening), and whether the RBI moves before or after the Fed.",
    ),
    "inCpi": dict(
        what="How much prices of everyday goods and services in India rose compared with a year ago (headline CPI, combined rural and urban).",
        source="Ministry of Statistics (MoSPI), around the 12th of the next month. The base year changed to 2024 from January 2026. Filled in data/manual/rbi.csv.",
        read="The RBI's target is 4%, with a band of 2–6%. Above 6% breaks the upper limit and puts pressure on the RBI to hike. Food (vegetables, pulses) makes it swing a lot.",
        path="High CPI → RBI keeps rates high or hikes → borrowing costs rise → slower growth and lower stock valuations. "
             "Oil and a weak rupee both push CPI up.",
        watch="Breaks above 6% (like October 2026) and core inflation, which leaves out food and fuel.",
    ),
    "fx": dict(
        what="India's foreign exchange reserves: dollars, other currencies, gold and IMF holdings kept by the RBI. "
             "They are the RBI's ammunition to steady the rupee.",
        source="RBI weekly statistical supplement. This chart uses FRED's monthly series, which leaves out gold, so it reads lower than the RBI's headline figure.",
        read="More reserves = more ability to defend the rupee. They fall when the RBI sells dollars to support the rupee. "
             "They were about $275B in 2013 and much higher in the 2020s.",
        path="FII selling or a high oil bill → rupee under pressure → RBI sells dollars → reserves fall and rupee cash leaves banks → tighter liquidity.",
        watch="Big monthly drops. These show how hard the RBI is defending the rupee.",
    ),
    "inLiq": dict(
        what="Whether Indian banks have spare cash (surplus) or are short of cash (deficit) in the system, based on the RBI's liquidity operations.",
        source="RBI daily liquidity data. Not filled yet; would go in data/manual/rbi.csv.",
        read="Surplus = easy money and lower short-term rates. Deficit = tight money. A deficit larger than ₹1 lakh crore is significant.",
        path="RBI selling dollars or tax outflows → less rupee cash → deficit → short-term rates rise → Bank Nifty under pressure.",
        watch="A swing from surplus into deficit.",
    ),
    "cad": dict(
        what="India's current account balance: everything India earns from abroad (exports, services, remittances) minus everything it pays abroad (imports, interest, dividends). "
             "A negative number is a deficit.",
        source="RBI quarterly balance of payments release, about 2–3 months after each quarter. Filled in data/manual/rbi.csv.",
        read="Around −1% to −2% of GDP is manageable. Below −2.5% is a warning. It was close to −5% in 2012–13, which is why the 2013 taper tantrum hit India so hard. "
             "A positive number is a surplus.",
        path="Bigger deficit → India needs more foreign money every month → more exposed to FII outflows → rupee weakens faster in a shock.",
        watch="Oil and gold imports pushing it wider, and how it changes over a few quarters rather than one.",
    ),
    "nifty": dict(
        what="The NSE's index of 50 large Indian companies. It is the main measure of the Indian stock market.",
        source="NSE, daily (Yahoo symbol ^NSEI).",
        read="Long-run growth is about 10–12% a year. A fall of 10% from the top is a correction, and 20% is a bear market. "
             "Its biggest falls were in 2008 (more than 50%) and 2020 (almost 40%).",
        path="It is at the end of the chain. It reacts to FII flows, the rupee, RBI rates, oil and global risk mood, and is cushioned by domestic SIP and mutual fund buying.",
        watch="Moves together with heavy FII selling and a weak rupee, and how far it falls compared with the S&P 500.",
    ),
    "bank": dict(
        what="The NSE index of the 12 most-traded banking stocks. It is the part of the market most sensitive to interest rates and liquidity.",
        source="NSE, daily (Yahoo symbol ^NSEBANK).",
        read="It moves more than the Nifty in both directions. It does well when rates fall and liquidity is plentiful, and badly when liquidity tightens.",
        path="RBI hikes or tight liquidity → higher funding costs and worries about bad loans → Bank Nifty falls. FIIs own a lot of bank stocks, so FII selling hits it hard.",
        watch="Underperformance versus the Nifty, which often signals tightening liquidity.",
    ),
    "sp": dict(
        what="The index of 500 large US companies. It is the main measure of the US stock market and of global risk appetite.",
        source="S&P Dow Jones Indices, daily (Yahoo symbol ^GSPC).",
        read="A fall of 10% is a correction, and 20% is a bear market. When it falls sharply, investors usually cut risk everywhere, including India.",
        path="US stocks fall → global risk-off → FIIs reduce emerging-market exposure → selling in India. Rising US stocks usually support flows into India.",
        watch="Falls together with rising VIX and a rising dollar, which is the classic risk-off mix.",
    ),
    "ndx": dict(
        what="The 100 largest non-financial companies on the Nasdaq exchange, dominated by big tech.",
        source="Nasdaq, daily (Yahoo symbol ^NDX).",
        read="It moves more than the S&P 500. Today it reflects the AI and big-tech trade. In 2000 it reflected the internet bubble.",
        path="Tech sell-offs hit global tech sentiment, including Indian IT stocks. Very large tech gains can also pull money away from emerging markets.",
        watch="Signs of a bubble: very fast gains concentrated in a few stocks, like 1999–2000.",
    ),
    "gold": dict(
        what="The price of gold in US dollars per ounce. It is a safe-haven asset and a hedge against inflation and a falling dollar.",
        source="COMEX gold futures, daily (Yahoo symbol GC=F).",
        read="It tends to rise when real interest rates fall, when there is fear, and when central banks buy. India is one of the biggest buyers of gold.",
        path="Higher gold prices → India's gold import bill rises → wider current account deficit → pressure on the rupee. "
             "It also signals that global investors are worried.",
        watch="Gold rising together with VIX (fear), or gold rising while the dollar also rises (unusual, signals deep stress).",
    ),
    "silver": dict(
        what="The price of silver in US dollars per ounce. It is part precious metal, part industrial metal (used in solar panels and electronics).",
        source="COMEX silver futures, daily (Yahoo symbol SI=F).",
        read="It moves much more than gold. It tends to do well when both fear and industrial demand are high.",
        path="Similar to gold for India's import bill. Big swings also affect silver ETFs, which are popular with Indian investors.",
        watch="The gold-to-silver price ratio, and very fast spikes that tend to reverse.",
    ),
    "vix": dict(
        what="The 'fear gauge': how much movement options traders expect in the S&P 500 over the next 30 days.",
        source="Cboe, daily (FRED series VIXCLS).",
        read="Below 15 = calm. 15–25 = normal worry. Above 30 = fear. Above 40 = panic. It hit about 80 in 2008 and 2020.",
        path="High VIX → investors cut risk worldwide → FII selling in India → higher India VIX and a falling Nifty.",
        watch="Sudden jumps above 30, and how fast it falls back.",
    ),
    "inVix": dict(
        what="India's fear gauge: how much movement options traders expect in the Nifty over the next 30 days.",
        source="NSE, daily (Yahoo symbol ^INDIAVIX). History starts around 2008.",
        read="Below 13 = calm. 13–20 = normal. Above 20 = fear. Above 30 = panic. It sets the price of options, which matters for option sellers and buyers.",
        path="It usually rises with global VIX, FII selling and big local events (elections, budgets). High India VIX means option premiums are expensive.",
        watch="Spikes before known events, and whether it rises while the Nifty is still calm, which is an early warning.",
    ),
}
