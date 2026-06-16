import http from 'k6/http';
import { check, sleep } from 'k6';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

export const options = {
    stages: [
        { duration: '10s', target: 20 },
        { duration: '20s', target: 50 },
        { duration: '10s', target: 0 },
    ],
    thresholds: {
        http_req_duration: ['p(95)<500'],
        http_req_failed: ['rate<0.01'],
    },
};

// Pre-create accounts (run once via a setup script, or use fixed IDs from your DB)
const ALICE_ID = 'FIXED-ALICE-UUID';
const BOB_ID = 'FIXED-BOB-UUID';

export default function () {
    const key = uuidv4();
    const payload = JSON.stringify({
        sender_id: ALICE_ID,
        receiver_id: BOB_ID,
        amount: '10.00',
    });
    
    const params = {
        headers: {
            'Content-Type': 'application/json',
            'Idempotency-Key': key,
        },
    };
    
    const res = http.post('http://localhost:8000/transactions', payload, params);
    
    check(res, {
        'is status 200': (r) => r.status === 200,
        'transaction completed': (r) => r.json('status') === 'COMPLETED',
    });
    
    sleep(0.1);
}
