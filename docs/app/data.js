/* ============================================================
   STATIC TEXT FOR THE LIFTIE SUTRAS PAGE
   Every number the page shows is written by scripts/build_app_model.py into model.js. This file holds only
   what the pipeline does not compute: real posts quoted as artifacts, the rename note, the 2026-27 outlook text
   and the one-post-three-readers example. The per-winter days, scores and wind lines in `strata` are replaced
   at load time by model.js (P.strata); the values here are fallbacks only.
   ============================================================ */
window.DATA = {
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
  readers: {
    post: "The Funitel is on wind hold. #palisadesops",
    parser: { label: "hold" },
    subq: { label: "hold", conf: 0.999 },
    muse: { label: "hold", conf: 1.0 }
  },
  agree: { posts: 7040, parser_subq: 0.931, parser_muse: 0.973, subq_muse: 0.946 }
};
