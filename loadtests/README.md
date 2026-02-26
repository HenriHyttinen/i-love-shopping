# Load Testing

This project includes three k6 scenarios:
- `k6/browse_catalog.js`
- `k6/search_and_pdp.js`
- `k6/cart_checkout.js`

## Run with local k6
```bash
BASE_URL=http://localhost:8000 k6 run loadtests/k6/browse_catalog.js
BASE_URL=http://localhost:8000 k6 run loadtests/k6/search_and_pdp.js
BASE_URL=http://localhost:8000 k6 run loadtests/k6/cart_checkout.js
```

## Run with Docker Compose profile
Start backend first:
```bash
docker-compose up --build -d
```

Run all load scenarios in one command:
```bash
docker-compose --profile loadtest run --rm k6
```
