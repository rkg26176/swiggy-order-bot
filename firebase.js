const admin = require('firebase-admin');

// Firebase Credentials Setup
const serviceAccount = {
  "type": "service_account",
  "project_id": "gbxswiggyorderbot",
  "private_key_id": "84cfae335cdb213afb8597b7f9d7827102ac1e11",
  "private_key": process.env.FIREBASE_PRIVATE_KEY || "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC80s3EoWNS/yqd\n7zUbmqvYSNlFu3PFqSSQ08o5Aoro7ov9yrhG5N1Ug7CJiN4lJ/ADD9YfLicvv8Xc\nS+GjwXXy/XsmRjMH1Z3nHePeHjXv76Az2jlRq0wZre3MK+NZVfSSdMnwAvcIhufR\njc36SRCxYNbSqBLtlSQbIz0R0McnJ01lOxVp3OSJp+HnrI7QktLvPjDHfEJiY8CK\n4rB4WjE3EqAF94tcdiDg2c2JBYm+HrmYKxDmwS9ad+Bs0PBQevcnNlwyb/Fjg99N\n6R/UM2uwlUtJQ3RTWH/GymUHtKX37xySkS0EuLzsHX/blNYw3gP5cD6Y8Q0lxy0F\nQU2qlGM5AgMBAAECggEAAm/CH7ZjbH8Ry6rulhkC/JPQzTRT5bW+6F2Fc+tUtRh/\nS1H08cq0Vyy2N+DY2P9CQKcihoXXKyfLlTwzEjvuoB2UPr0OKT+sjxXghLwZhOWv\n66te/m8F2LBBvVb06jbh9i8e/CZ4ja5L+N3eWYWXNWrAKueiOiq0YEBc1slU8gNr\nXrEcoNaFkZRlj65tSL/z3aVWunOixxqUgt6lvWGmcq7zIsTjtpuoasu0UCYPBqgw\npdQKY6rvW6wjCZdWiGy2NnP1h0V9BScnqB+KSmsTrb0vvnCV9+rejgNEtlAgs1N/\nxnKpms/phncXuW/0EADUNMKbdseHCjFblvE05zFreQKBgQDi+Y1ChawcSmHA1E+n\ncOwuTJrnosqJcQYT5Y1eZmy+hSFeRgFwB1s8rR2Dnkp1yJS8ZqrzQkAJWhHFc5v/\naF9N15cTbjUrnGfsdfD8rbiUEtHG5s7BbXG80Bj089C657bs2ndDsX2+DXhBgY03\n30BfZmrpuVQaBscJHUueByvQlQKBgQDU+EubLfrbyGZ2lSJ2fYG33n/keMCYlwVt\nBa+ewhJgMoRSFdCBuCxDKIohCjlvkzOYfnhw1vkuPRg3e8FyC34qxJG8jcNxQAus\nZGIEXltiulskEcdsMxLpR2gAtY+KFbtTzKnSiGuk6wjqsncA66XOzbGeQs9EzRCU\niPubuxZrFQKBgDwEAn8Re2XroRdszDcZG8pORTN0jxtygEnoi83nRV/HMgCMgDrQ\nJybPG5u+0i98vx9mAlPaM7aFU2ejXx9UyMZ7eB4SKQsEC1KyCOu3P7Qfmcp/IzJw\nLv/fAopaodmaBXtxdNG4b+g+BYtEp0Oby5iuKxzr/Tn4is51KZZ6jPJVAoGBAMNm\nNOhiHYI9slUmrAIPUU9EZA9aA0t9dMr8po+A/J8qemFeBnqeYm4T6fg6i0wlwPcv\nQo41j1avU2LEt05N4SqYRCa94w4rdwpq58ueTzacSTck4NYTXkyO6YuNCe/l1IQk\nicPSywD7bKj5qVo821qNO2Q7ZDR5+bZuoHvYAc+pAoGBAKiGb/v0wX6WyJIhM1wI\nxpNNr9hjokwNB/yCf9NI5hemqNEZwVfJrQnQeLS5Hf5RwBgdGBhzh+eGeFH1aBVl\EoDIhmH/X2hEYWR9iWs04qwgFo3COWgPMEYP7DpmnZIOLVfOscklqAxCQKn9JeNF\nlS8Z2pa0B781dix3Sie6imJj\n-----END PRIVATE KEY-----\n".replace(/\\n/g, '\n'),
  "client_email": "firebase-adminsdk-fbsvc@gbxswiggyorderbot.iam.gserviceaccount.com",
  "client_id": "110587120076476207444",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40gbxswiggyorderbot.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
};

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

const db = admin.firestore();
module.exports = { db };
