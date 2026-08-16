'use strict';

const { astro, util } = require('iztro');

astro.config({
  yearDivide: 'exact',
  horoscopeDivide: 'exact',
  dayDivide: 'forward',
  ageDivide: 'normal',
  algorithm: 'default',
});

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', () => {
  const cases = JSON.parse(input);
  const results = cases.map((item) => {
    const chart = astro.bySolar(item.date, item.time_index, item.sex, true, 'zh-CN');
    const mutagens = Object.fromEntries(chart.palaces
      .flatMap((palace) => [...palace.majorStars, ...palace.minorStars])
      .filter((star) => star.mutagen)
      .map((star) => [star.mutagen, star.name]));
    const yearly = chart.horoscope(item.date, 6).yearly;
    const starBranch = {};
    chart.palaces.forEach((palace) => {
      [...palace.majorStars, ...palace.minorStars].forEach((star) => {
        starBranch[star.name] = palace.earthlyBranch;
      });
    });
    const mutagedPlaces = Object.fromEntries(chart.palaces.map((palace) => [
      palace.earthlyBranch,
      // mutagedPlaces() lacks its astrolabe back-reference in 2.5.8, assemble manually.
      util.getMutagensByHeavenlyStem(palace.heavenlyStem).map((star) => starBranch[star]),
    ]));
    const result = {
      year_stem: chart.rawDates.chineseDate.yearly[0],
      life_branch: chart.earthlyBranchOfSoulPalace,
      body_branch: chart.earthlyBranchOfBodyPalace,
      palace_branches: chart.palaces.map((palace) => palace.earthlyBranch).sort(),
      palace_stems: Object.fromEntries(chart.palaces.map((palace) => [
        palace.earthlyBranch,
        palace.heavenlyStem,
      ])),
      mutaged_places: mutagedPlaces,
      decadal_ranges: Object.fromEntries(chart.palaces.map((palace) => [
        palace.earthlyBranch,
        palace.decadal.range,
      ])),
      minor_limit_ages: Object.fromEntries(chart.palaces.map((palace) => [
        palace.earthlyBranch,
        palace.ages,
      ])),
      major_stars: Object.fromEntries(chart.palaces.map((palace) => [
        palace.earthlyBranch,
        palace.majorStars.map((star) => star.name).sort(),
      ])),
      major_star_brightness: Object.fromEntries(chart.palaces.map((palace) => [
        palace.earthlyBranch,
        palace.majorStars.map((star) => [star.name, star.brightness]),
      ])),
      minor_stars: Object.fromEntries(chart.palaces.map((palace) => [
        palace.earthlyBranch,
        palace.minorStars.map((star) => star.name).sort(),
      ])),
      birth_mutagens: ['禄', '权', '科', '忌'].map((mutagen) => ({
        star: mutagens[mutagen],
        mutagen,
      })),
      annual_year_pillar: `${yearly.heavenlyStem}${yearly.earthlyBranch}`,
      annual_palaces: yearly.palaceNames,
    };
    if (item.horo_date) {
      const horo = chart.horoscope(item.horo_date, 6);
      result.horoscope = {
        nominal_age: horo.age.nominalAge,
        decadal: {
          index: horo.decadal.index,
          pillar: `${horo.decadal.heavenlyStem}${horo.decadal.earthlyBranch}`,
          mutagen: horo.decadal.mutagen,
          is_childhood: horo.decadal.name === '童限',
        },
        yearly: {
          index: horo.yearly.index,
          pillar: `${horo.yearly.heavenlyStem}${horo.yearly.earthlyBranch}`,
          mutagen: horo.yearly.mutagen,
          stars: horo.yearly.stars.map((bucket) => bucket.map((star) => star.name)),
        },
      };
    }
    return result;
  });
  process.stdout.write(JSON.stringify(results));
});
