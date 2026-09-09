/*
 * Sample profiles for the prototype. Every person here is fictional.
 * Departments mirror BKSE's corporate functions; neighborhoods are real.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.KYN = Object.assign(root.KYN || {}, factory());
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const DEPARTMENTS = [
    'Ticketing', 'Sales', 'Partnerships', 'Marketing', 'Operations',
    'Finance', 'People & Culture', 'Legal', 'Digital', 'Community Relations', 'Guest Experience',
  ];

  const INTERESTS = [
    'pickup basketball', 'running', 'ceramics', 'cycling', 'live music', 'cooking',
    'board games', 'yoga', 'film', 'photography', 'karaoke', 'pickleball', 'bouldering',
    'trivia', 'gardening', 'vinyl', 'soccer', 'tennis', 'birding', 'chess', 'crosswords',
    'hiking', 'salsa dancing', 'baking', 'thrifting', 'stand-up comedy', 'swimming',
  ];

  // Teams people follow. Nets and Liberty are the home teams; the rest is where the arguments start.
  const TEAMS = [
    'Nets', 'Liberty', 'Knicks', 'Yankees', 'Mets', 'Giants', 'Jets', 'Rangers', 'Islanders', 'Devils',
    'NYCFC', 'Red Bulls', 'Gotham FC', 'Brooklyn Cyclones', 'Arsenal', 'Barcelona', 'Syracuse basketball', 'UConn women\'s basketball',
  ];

  const ELIGIBLE_HEADCOUNT = 140; // corporate staff invited to the pilot

  const SEED_PROFILES = [
    p('p01', 'Maya Okafor', 'Ticketing', 'Box Office Manager', 'Crown Heights', ['pickup basketball', 'live music', 'trivia'], ['Chuko', 'Olmsted'], ['Nets', 'Liberty', 'Knicks']),
    p('p02', 'Daniel Reyes', 'Sales', 'Premium Sales Executive', 'Astoria', ['soccer', 'cooking', 'karaoke'], ['Taverna Kyclades', 'Los Tacos No. 1'], ['Mets', 'Barcelona', 'NYCFC']),
    p('p03', 'Priya Raman', 'Partnerships', 'Partnership Marketing Manager', 'Park Slope', ['running', 'ceramics', 'crosswords'], ['Miriam', 'Olmsted'], ['Liberty', 'Yankees']),
    p('p04', 'Jordan Bell', 'Marketing', 'Brand Manager', 'Bed-Stuy', ['vinyl', 'photography', 'live music'], ["Peaches", 'Saraghina'], ['Nets', 'Giants']),
    p('p05', 'Sofia Marchetti', 'Operations', 'Event Operations Lead', 'Bay Ridge', ['cycling', 'baking', 'board games'], ['Tanoreen', 'Lucali'], ['Yankees', 'Islanders']),
    p('p06', 'Ethan Cole', 'Finance', 'Senior Financial Analyst', 'Long Island City', ['running', 'chess', 'film'], ['Casa Enrique', 'Xi\'an Famous Foods'], ['Mets', 'Rangers']),
    p('p07', 'Aisha Diallo', 'People & Culture', 'HR Business Partner', 'Harlem', ['salsa dancing', 'cooking', 'yoga'], ["Sylvia's", "Melba's"], ['Liberty', 'Knicks', 'Giants']),
    p('p08', 'Liam Nguyen', 'Digital', 'Product Manager, App', 'Williamsburg', ['bouldering', 'film', 'board games'], ["Peter Luger", "Lilia"], ['Nets', 'Arsenal']),
    p('p09', 'Hannah Goldberg', 'Legal', 'Associate Counsel', 'Upper West Side', ['tennis', 'crosswords', 'hiking'], ["Barney Greengrass", "Jacob's Pickles"], ['Yankees', 'Rangers']),
    p('p10', 'Marcus Thompson', 'Community Relations', 'Community Programs Manager', 'Flatbush', ['pickup basketball', 'stand-up comedy', 'cooking'], ["Peppa's", 'Di Fara'], ['Nets', 'Knicks', 'Jets']),
    p('p11', 'Chloe Dubois', 'Guest Experience', 'Guest Services Supervisor', 'Prospect Heights', ['ceramics', 'thrifting', 'live music'], ['Chuko', 'Olmsted'], ['Liberty', 'Gotham FC']),
    p('p12', 'Omar Haddad', 'Ticketing', 'Ticket Operations Analyst', 'Jackson Heights', ['soccer', 'photography', 'trivia'], ['Phayul', 'Arepa Lady'], ['Red Bulls', 'Barcelona', 'Mets']),
    p('p13', 'Grace Kim', 'Sales', 'Group Sales Manager', 'Astoria', ['yoga', 'karaoke', 'baking'], ['Taverna Kyclades', 'Titan Foods'], ['Mets', 'Jets']),
    p('p14', 'Tomás Herrera', 'Partnerships', 'Partnership Activation Coordinator', 'Sunset Park', ['cycling', 'soccer', 'salsa dancing'], ['Tacos El Bronco', 'Nom Wah'], ['NYCFC', 'Barcelona']),
    p('p15', 'Rachel Stein', 'Marketing', 'Social Media Manager', 'Greenpoint', ['thrifting', 'vinyl', 'swimming'], ['Lilia', 'Karczma'], ['Liberty', 'Rangers']),
    p('p16', 'Andre Williams', 'Operations', 'Facilities Coordinator', 'Mott Haven', ['pickup basketball', 'chess', 'stand-up comedy'], ['La Morada', 'Xi\'an Famous Foods'], ['Yankees', 'Knicks']),
    p('p17', 'Nina Petrova', 'Finance', 'Payroll Specialist', 'Forest Hills', ['tennis', 'gardening', 'film'], ['Nick\'s Pizza', 'Dee\'s'], ['Mets', 'Islanders']),
    p('p18', 'Kwame Asante', 'Digital', 'Data Engineer', 'Fort Greene', ['running', 'bouldering', 'trivia'], ['Miss Ada', 'Olmsted'], ['Nets', 'Arsenal', 'Syracuse basketball']),
    p('p19', 'Isabella Rossi', 'Legal', 'Contracts Manager', 'Hoboken', ['hiking', 'cooking', 'birding'], ['Fiore\'s', 'La Isla'], ['Devils', 'Giants']),
    p('p20', 'Devon Carter', 'Guest Experience', 'Accessibility Coordinator', 'Clinton Hill', ['board games', 'baking', 'film'], ['Speedy Romeo', 'Miss Ada'], ['Nets', 'Liberty']),
    p('p21', 'Yuki Tanaka', 'Community Relations', 'Youth Programs Lead', 'Sunnyside', ['swimming', 'photography', 'ceramics'], ['Casa Enrique', 'Salt & Fat'], ['Mets', 'Gotham FC']),
    p('p22', 'Samuel Adeyemi', 'People & Culture', 'Talent Acquisition Partner', 'Bushwick', ['live music', 'karaoke', 'pickup basketball'], ["Roberta's", 'Saraghina'], ['Nets', 'Knicks', 'Giants']),
    p('p23', 'Elena Vasquez', 'Marketing', 'Creative Director', 'East Village', ['film', 'vinyl', 'stand-up comedy'], ['Superiority Burger', "Veselka"], ['Yankees', 'Liberty']),
    p('p24', 'Ben Fischer', 'Ticketing', 'Season Ticket Services Rep', 'Windsor Terrace', ['running', 'birding', 'crosswords'], ['Della', 'Lucali'], ['Brooklyn Cyclones', 'Mets', 'Jets']),
  ];

  function p(id, name, department, title, neighborhood, interests, restaurants, teams) {
    return { id, name, department, title, neighborhood, interests, restaurants, teams, optedIn: true };
  }

  return { DEPARTMENTS, INTERESTS, TEAMS, ELIGIBLE_HEADCOUNT, SEED_PROFILES };
});
