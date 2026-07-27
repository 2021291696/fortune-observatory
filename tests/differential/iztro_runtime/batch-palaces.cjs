'use strict';

const { astro } = require('iztro');

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
    return {
      year_stem: chart.rawDates.chineseDate.yearly[0],
      life_branch: chart.earthlyBranchOfSoulPalace,
      body_branch: chart.earthlyBranchOfBodyPalace,
      palace_branches: chart.palaces.map((palace) => palace.earthlyBranch).sort(),
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
  });
  process.stdout.write(JSON.stringify(results));
});
