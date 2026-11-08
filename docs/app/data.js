/* ============================================================
   DATA FOR THE LIFTIE SUTRAS PAGE  (the only file that changes)
   Everything the page shows comes from window.DATA.
   To plug in final results: replace the values below, keep the keys.
   Set meta.draft = false to hide the "draft data" ribbon.

   Keys:
   meta       title, subtitle, tagline, draft, note
   facts      one-line stats under the hero: {label, value}
   strata[]   one per winter, NEWEST FIRST: winter, era ("Squaw Valley"|"Palisades Tahoe"),
              phase ("El Niño"|"La Niña"|"neutral"), strength, days (days with posts), wind_holds,
              score (rules, 0-1), baseline (simple wind rule, 0-1),
              artifact {date, text}  <- a real post from that winter
   renamed    text shown between the two eras
   days[]     replay mornings: id, label, verdict ("hit"|"miss"|"calm"), readings {early_gust, day_gust, top_gust, snow},
              chain[] {name, tier ("gate"|"upper"|"lower")}, predicted{name:state}, actual{name:state},
              sutras[] {lift, text, odds, ink, pencil, evidence[]}, torn (bool), tornNote, posts[] {t, text}
              states: "hold" | "spin" | "delay" | "unknown" (actual only)
   readers    one post read three ways: post, parser{label}, subq{label, conf}, muse{label, conf}
   agree      {posts, parser_subq, parser_muse, subq_muse}  (fractions)
   unexplained[] {lift, pct, of, note}
   ============================================================ */
window.DATA = {
  meta: {
    title: "The Liftie Sutras",
    subtitle: "Send It or End It",
    tagline: "The unwritten rules that decide when Palisades lifts hold, recovered from eight winters of posts.",
    draft: true,
    note: "Draft data: replay mornings and predictions are placeholders until the hidden-winter results plug in."
  },
  facts: [
    { label: "winters dug up", value: "8" },
    { label: "posts read", value: "7,040" },
    { label: "independent readers", value: "3" },
    { label: "rules recovered", value: "39" }
  ],
  drift: { old: { date: "Winter 2020-21", text: "The wind is howling out there! All upper mountain lifts at Squaw, including the Tram and Squaw One, will start the day on wind hold. #squawlifts" }, new: { date: "Winter 2024-25", text: "At Palisades, Upper Mountain is off the schedule for today, including Wa She Shu, Tram, Funitel. Lower Mountain is on patrol hold (Exhibition, Far East, KT-22, Red Dog, Resort Chair). #palisadesops" }, marks: ["Squaw","#squawlifts","Palisades","#palisadesops"] },
  outlook: {
    lines: [
      "NOAA (Oct 8, 2026): a strong to very strong El Niño is expected to last through the winter.",
      "Three seasonal models (SF Chronicle, Oct 17): about 17% less Tahoe snow than normal in Nov-Dec and about 28% more in Jan-Mar. The models disagree with each other.",
      "OpenSnow, the resort's weather partner, calls for above-average Tahoe snowfall.",
      "Warm storms can rain at the 6,200 ft base while snowing on the upper mountain. This tool does not model rain or snow level."
    ],
    method: "Each button sets the sliders to the median of matching days from the three El Niño winters in our data (2018-19 and 2019-20 weak, 2023-24 strong). It shows what days like these tend to look like, not what will happen."
  },
  renamed: "Mid-dig, in 2021, the resort changed its name: Squaw Valley Alpine Meadows became Palisades Tahoe, and two lifts were renamed with it. Squaw One is now Wa She Shu; Squaw Creek is now Resort Chair. Same lifts, new words. The parser folds the old names into the new so each lift keeps one history.",
  strata: [
    { winter: "2025-26", era: "Palisades Tahoe", phase: "neutral", strength: "", days: 90, wind_holds: 21, score: 0.702, baseline: 0.375, line: 60.1,
      artifact: { date: "Winter 2025-26", text: "Alpine lifts are scheduled to open at 9am. Scott and Summit are on wind hold. Mountain Ops is working hard on snow mitigation. Projected opening for lower mountain at Palisades is 10am, with upper mountain goal for 12pm." } },
    { winter: "2024-25", era: "Palisades Tahoe", phase: "neutral", strength: "", days: 127, wind_holds: 50, score: 0.852, baseline: 0.601, line: 60.1,
      artifact: { date: "Jan 20, 2025", text: "Due to significant winds on the Upper Mountain, the Base to Base Gondola, Granite Chief, Emigrant, and Siberia will start the day on wind hold. #palisadesops" } },
    { winter: "2023-24", era: "Palisades Tahoe", phase: "El Niño", strength: "strong", days: 169, wind_holds: 50, score: 0.765, baseline: 0.478, line: 61.2,
      artifact: { date: "Winter 2023-24", text: "Due to increasing winds, all upper mountain lifts are now on wind hold. #palisadesops" } },
    { winter: "2022-23", era: "Palisades Tahoe", phase: "La Niña", strength: "", days: 187, wind_holds: 70, score: 0.870, baseline: 0.540, line: 60.6,
      artifact: { date: "Winter 2022-23", text: "All upper mountain lifts have been removed from the schedule for today: Tram, Bailey's Beach, Gold Coast, Mountain Meadow, Shirley Lake, Siberia, Solitude. The Funitel will remain on a wind hold. #palisadesops" } },
    { winter: "2021-22", era: "Palisades Tahoe", phase: "La Niña", strength: "", days: 157, wind_holds: 46, score: 0.786, baseline: 0.465, line: 60.9,
      artifact: { date: "Winter 2021-22", text: "All upper mountain lifts currently have an anticipated weather impact. We'll update you as we know more. #palisadesops" } },
    { winter: "2020-21", era: "Squaw Valley", phase: "La Niña", strength: "", days: 115, wind_holds: 51, score: 0.830, baseline: 0.619, line: 60.1,
      artifact: { date: "Winter 2020-21", text: "The wind is howling out there! All upper mountain lifts at Squaw, including the Tram and Squaw One, will start the day on wind hold. #squawlifts" } },
    { winter: "2019-20", era: "Squaw Valley", phase: "El Niño", strength: "weak", days: 82, wind_holds: 45, score: 0.839, baseline: 0.672, line: 58.8,
      artifact: { date: "Winter 2019-20", text: "All upper mountain lifts at Squaw Valley will begin the day on wind hold. The Funitel will open as scheduled. #Squawlifts" } },
    { winter: "2018-19", era: "Squaw Valley", phase: "El Niño", strength: "weak", days: 125, wind_holds: 69, score: 0.881, baseline: 0.718, line: 61.2,
      artifact: { date: "Winter 2018-19", text: "Due to high winds across our upper mountains, the Tram, Mountain Meadow, and Granite Chief are now on Wind Hold. The Tram will continue to download guests at this time. #squawlifts" } }
  ],
  days: [
    {
      id: "dec16", label: "Mon Dec 16, 2024", verdict: "hit",
      readings: { early_gust: 87.6, day_gust: 114.7, top_gust: 46.4, snow: 0.0 },
      chain: [
        { name: "Base to Base", tier: "gate" }, { name: "Tram", tier: "gate" }, { name: "Funitel", tier: "gate" },
        { name: "Wa She Shu", tier: "upper" }, { name: "Siberia", tier: "upper" }, { name: "Gold Coast", tier: "upper" },
        { name: "Big Blue", tier: "upper" }, { name: "Shirley Lake", tier: "upper" }, { name: "Granite Chief", tier: "upper" },
        { name: "Mountain Meadow", tier: "upper" }, { name: "Bailey's Beach", tier: "upper" }, { name: "Belmont", tier: "upper" },
        { name: "Exhibition", tier: "lower" }, { name: "Red Dog", tier: "lower" }, { name: "Resort Chair", tier: "lower" }
      ],
      predicted: { "Base to Base": "hold", "Tram": "hold", "Funitel": "hold", "Wa She Shu": "hold", "Siberia": "hold", "Gold Coast": "hold", "Big Blue": "hold", "Shirley Lake": "hold", "Granite Chief": "hold", "Mountain Meadow": "hold", "Bailey's Beach": "hold", "Belmont": "hold", "Exhibition": "spin", "Red Dog": "spin", "Resort Chair": "spin" },
      actual:    { "Base to Base": "hold", "Tram": "hold", "Funitel": "hold", "Wa She Shu": "unknown", "Siberia": "hold", "Gold Coast": "hold", "Big Blue": "hold", "Shirley Lake": "hold", "Granite Chief": "hold", "Mountain Meadow": "hold", "Bailey's Beach": "hold", "Belmont": "unknown", "Exhibition": "spin", "Red Dog": "spin", "Resort Chair": "spin" },
      sutras: [
        { lift: "The Tram", text: "When the day's gusts reach 71 mph, the Tram holds 2 days in 3 (59 of 90). Below that, about 1 day in 17.", odds: "2 in 3",
          ink: "Operators named wind on 60 of the Tram's 76 hold days.", pencil: "The 71 mph line was worked out from weather.",
          evidence: ["07:48  The Base to Base Gondola, Tram, Mountain Meadow, Granite and Bailey's Beach will start the day on wind hold."] },
        { lift: "The Funitel", text: "At 97 mph the Funitel holds 7 days in 10 (30 of 43). Below that, about 1 day in 14.", odds: "7 in 10",
          ink: "Wind was stated on 24 of its 55 hold days.", pencil: "The 97 mph line was worked out from weather.",
          evidence: ["09:43  The Funitel is on wind hold.", "10:53  Funitel, Tram, Bailey's Beach, Big Blue, Gold Coast, Granite Chief, Mountain Meadow, Shirley Lake and Siberia are now closed for the day due to winds."] }
      ],
      torn: false,
      posts: [
        { t: "06:16", text: "Palisades: snow, high of 34, SW winds 20+. 17 lifts/wind holds possible." },
        { t: "07:48", text: "The Base to Base Gondola, Tram, Mountain Meadow, Granite and Bailey's Beach will start the day on wind hold." },
        { t: "09:43", text: "The Funitel is on wind hold." },
        { t: "09:44", text: "Gold Coast, Siberia and Shirley are on wind hold." },
        { t: "10:53", text: "Funitel, Tram, Bailey's Beach, Big Blue, Gold Coast, Granite Chief, Mountain Meadow, Shirley Lake and Siberia are now closed for the day due to winds." }
      ]
    },
    {
      id: "dec15", label: "Sun Dec 15, 2024", verdict: "miss",
      readings: { early_gust: 22.4, day_gust: 48.1, top_gust: 21.7, snow: 2.1 },
      chain: [
        { name: "Base to Base", tier: "gate" }, { name: "Tram", tier: "gate" }, { name: "Funitel", tier: "gate" },
        { name: "Siberia", tier: "upper" }, { name: "Gold Coast", tier: "upper" }, { name: "Big Blue", tier: "upper" },
        { name: "Granite Chief", tier: "upper" }, { name: "Mountain Meadow", tier: "upper" }, { name: "Bailey's Beach", tier: "upper" },
        { name: "Red Dog", tier: "lower" }, { name: "Resort Chair", tier: "lower" }, { name: "First Venture", tier: "lower" }
      ],
      predicted: { "Base to Base": "spin", "Tram": "spin", "Funitel": "spin", "Siberia": "spin", "Gold Coast": "spin", "Big Blue": "spin", "Granite Chief": "spin", "Mountain Meadow": "spin", "Bailey's Beach": "spin", "Red Dog": "spin", "Resort Chair": "spin", "First Venture": "spin" },
      actual:    { "Base to Base": "delay", "Tram": "delay", "Funitel": "delay", "Siberia": "delay", "Gold Coast": "delay", "Big Blue": "delay", "Granite Chief": "delay", "Mountain Meadow": "delay", "Bailey's Beach": "delay", "Red Dog": "spin", "Resort Chair": "spin", "First Venture": "spin" },
      sutras: [],
      torn: true,
      tornNote: "Winds were light and no sutra fires, yet the gate lifts opened late and no cause was given. This is a missing page, and we label it that way.",
      posts: [
        { t: "05:41", text: "7\" overnight for a 24 hour snow total of up to 17\" and storm total of 43\". Today's forecast is for sunshine, high of 34 and calm winds." },
        { t: "09:24", text: "Upper Mountain at Palisades expected at 9:30/9:45am." },
        { t: "09:55", text: "Open at Palisades: B2B Gondola, Tram, First Venture & Carpet, Red Dog, Resort Chair, Funitel, Gold Coast, Siberia, Big Blue, Bailey's, Mountain Meadow, Granite Chief." }
      ]
    },
    {
      id: "dec18", label: "Wed Dec 18, 2024", verdict: "calm",
      readings: { early_gust: 32.7, day_gust: 32.7, top_gust: 18.5, snow: 0.1 },
      chain: [
        { name: "Base to Base", tier: "gate" }, { name: "Tram", tier: "gate" }, { name: "Funitel", tier: "gate" },
        { name: "Siberia", tier: "upper" }, { name: "Gold Coast", tier: "upper" }, { name: "Big Blue", tier: "upper" },
        { name: "Granite Chief", tier: "upper" }, { name: "Mountain Meadow", tier: "upper" }, { name: "Bailey's Beach", tier: "upper" },
        { name: "Red Dog", tier: "lower" }, { name: "Resort Chair", tier: "lower" }, { name: "First Venture", tier: "lower" }
      ],
      predicted: { "Base to Base": "spin", "Tram": "spin", "Funitel": "spin", "Siberia": "spin", "Gold Coast": "spin", "Big Blue": "spin", "Granite Chief": "spin", "Mountain Meadow": "spin", "Bailey's Beach": "spin", "Red Dog": "spin", "Resort Chair": "spin", "First Venture": "spin" },
      actual:    { "Base to Base": "spin", "Tram": "spin", "Funitel": "spin", "Siberia": "spin", "Gold Coast": "spin", "Big Blue": "spin", "Granite Chief": "spin", "Mountain Meadow": "spin", "Bailey's Beach": "spin", "Red Dog": "spin", "Resort Chair": "spin", "First Venture": "spin" },
      sutras: [],
      torn: false,
      posts: [{ t: "", text: "No hold was recorded for the gate lifts that day." }]
    }
  ],
  readers: {
    post: "The Funitel is on wind hold. #palisadesops",
    parser: { label: "hold" },
    subq: { label: "hold", conf: 0.999 },
    muse: { label: "hold", conf: 1.0 }
  },
  agree: { posts: 7040, parser_subq: 0.928, parser_muse: 0.969, subq_muse: 0.946 },
  unexplained: [
    { lift: "Funitel", pct: 22, of: "holds", note: "12 of 55 holds came with no stated cause" },
    { lift: "Tram", pct: 9, of: "holds", note: "7 of 76 holds came with no stated cause" }
  ]
};
