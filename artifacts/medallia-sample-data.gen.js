// Deterministic sample Medallia export for Riverside Arena (example data)
let seed = 20260902;
function rnd(){ seed = (seed*1103515245+12345) & 0x7fffffff; return seed/0x7fffffff; }
function pick(a){ return a[Math.floor(rnd()*a.length)]; }
function clamp(v,lo,hi){ return Math.max(lo,Math.min(hi,v)); }
function gauss(mu,sd){ let u=rnd()||1e-6,v=rnd(); return mu+sd*Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v); }

const events = [
 // date, name, type
 ["2026-07-03","Summer Sound Tour","Concert"],
 ["2026-07-10","Riverside Valkyries vs. Storm","Basketball"],
 ["2026-07-17","Ice Kingdom Live","Family Show"],
 ["2026-07-24","Riverside Valkyries vs. Aces","Basketball"],
 ["2026-07-31","Midnight Static","Concert"],
 ["2026-08-07","Riverside Valkyries vs. Sparks","Basketball"],
 ["2026-08-14","Neon Cathedral Tour","Concert"],
 ["2026-08-15","Neon Cathedral Tour (Night 2)","Concert"],
 ["2026-08-21","Riverside Valkyries vs. Liberty","Basketball"],
 ["2026-08-28","Big Laughs Comedy Festival","Comedy"],
];
const tiers = ["General Admission","Lower Bowl","Premium Club","Suite"];
const touch = {
 "Parking & Arrival": { base:{jul:7.6,aug:7.2}, concertPenalty:0.9,
   pos:["Parking was easy, in and out in ten minutes.","Pre-paid parking worked great, straight into the garage.","Arrival was smooth, staff waved us right in."],
   neg:["Took 45 minutes to get out of the garage after the show.","Parking signage was confusing, ended up circling twice.","Rideshare pickup zone was chaos, no staff directing anyone.","Paid $40 for parking and still walked 15 minutes."]},
 "Entry & Security": { base:{jul:7.5,aug:8.1},
   pos:["The new express lanes made security painless.","Walked through the gates in under five minutes, huge improvement.","Bag check was quick and the staff were friendly.","Entry was way faster than last season."],
   neg:["Line at the north gate wrapped around the block.","Security made me throw out a sealed water bottle.","Only two lanes open at Gate C, took 25 minutes."]},
 "Concessions": { base:{jul:7.6,aug:5.7},
   pos:["Loved the new local food stalls on the concourse.","Beer was cold and the line moved fast.","Good variety, prices are what you expect."],
   neg:["Waited 30 minutes for a hot dog and missed the opening act.","The new self-checkout kiosks kept freezing.","Stand ran out of pretzels by the second quarter.","$18 for a beer is too much.","Grab & Go stand had one person working, line was 40 deep.","Kiosk wouldn't take my card, had to wait for a staffer."]},
 "Restrooms": { base:{jul:7.3,aug:7.2},
   pos:["Restrooms were clean, even at halftime.","Plenty of restrooms, no wait."],
   neg:["Women's restroom on 200 level was out of paper towels.","Long restroom lines at intermission.","Floors were wet and nobody cleaned it up."]},
 "Seat & Sightlines": { base:{jul:8.3,aug:8.4},
   pos:["Great view from section 114, worth every penny.","Sound was crisp everywhere we sat.","Seats were comfortable and the sightlines were perfect."],
   neg:["Obstructed view from 218, the rigging blocked the screen.","Seats are too narrow for a three hour show."]},
 "Staff & Hospitality": { base:{jul:8.0,aug:8.1},
   pos:["Usher in section 105 went above and beyond finding our seats.","Every staff member we met was warm and helpful.","Guest services fixed our ticket issue in two minutes."],
   neg:["Staff at the concession stand seemed overwhelmed and rude.","Couldn't find an usher when we needed one."]},
 "Premium Clubs": { base:{jul:8.6,aug:8.8}, premiumOnly:true,
   pos:["The Riverside Club was excellent, food and service top notch.","Club lounge was a great escape from the crowd.","Suite attendant anticipated everything we needed."],
   neg:["Club bar ran out of the featured cocktail early.","Club was overcrowded during the break."]},
 "Mobile Tickets & App": { base:{jul:7.9,aug:6.8},
   pos:["Tickets loaded instantly, scanning was easy.","App wayfinding got us to our seats fast."],
   neg:["Ticket transfer failed twice before the show, nearly missed entry.","App crashed at the gate and I had no signal to reload it.","Couldn't get my tickets to show in the wallet, had to go to box office."]},
};
const rows=[];
let id=41870;
for(const [date,name,type] of events){
  const month = date.slice(5,7)==="07"?"jul":"aug";
  const n = type==="Concert"? 22 : type==="Basketball"? 16 : 14;
  for(let i=0;i<n;i++){
    const tier = pick(tiers.concat(["General Admission","Lower Bowl","General Admission"]));
    let keys=Object.keys(touch).filter(k=>!touch[k].premiumOnly || tier==="Premium Club"||tier==="Suite");
    const tp = pick(keys.concat(["Concessions","Concessions"])); const t=touch[tp];
    let mu = t.base[month];
    if(tp==="Parking & Arrival" && type==="Concert") mu -= t.concertPenalty;
    if(tp==="Mobile Tickets & App" && date.startsWith("2026-08-14")) mu -= 1.4;
    if(tp==="Concessions" && month==="aug" && type==="Concert") mu -= 0.5;
    if(tier==="Premium Club"||tier==="Suite") mu += 0.4;
    const osat = clamp(Math.round(gauss(mu,1.6)),1,10);
    const ltr = clamp(Math.round(gauss(osat+0.3,1.2)),0,10);
    let verb="";
    const r=rnd();
    if(osat<=6 && r<0.85) verb=pick(t.neg);
    else if(osat>=8 && r<0.55) verb=pick(t.pos);
    else if(r<0.2) verb=osat>=7?pick(t.pos):pick(t.neg);
    rows.push([id++,date,name,type,tier,tp,osat,ltr,verb]);
  }
}
const esc=s=>/[",\n]/.test(String(s))?`"${String(s).replace(/"/g,'""')}"`:s;
const out=["Response ID,Event Date,Event,Event Type,Seating Tier,Touchpoint,OSAT,LTR,Verbatim", ...rows.map(r=>r.map(esc).join(","))].join("\n");
require('fs').writeFileSync(process.argv[2], out);
console.log(rows.length,"rows");
