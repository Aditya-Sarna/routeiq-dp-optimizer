/**
 * ============================================================
 *  ROUTE OPTIMIZER — Held-Karp Dynamic Programming TSP Solver
 *  Industry Use: Delivery routing, logistics, fleet management
 *
 *  Algorithm: Held-Karp (exact DP solution to TSP)
 *  Time Complexity: O(n^2 * 2^n)
 *  Space Complexity: O(n * 2^n)
 *
 *  Used by: Amazon, FedEx, UPS for last-mile delivery routing
 * ============================================================
 */

#include <iostream>
#include <vector>
#include <algorithm>
#include <iomanip>
#include <climits>
using namespace std;

const double INF = 1e18;

struct Result {
    double cost;
    vector<int> path;
};

/**
 * Held-Karp DP TSP Solver
 * @param dist  NxN distance/cost matrix
 * @param n     Number of cities/nodes
 * @return      Optimal cost and path
 */
Result heldKarp(const vector<vector<double>>& dist, int n) {
    // dp[mask][i] = min cost to visit exactly the cities in 'mask', ending at city i
    int states = 1 << n;
    vector<vector<double>> dp(states, vector<double>(n, INF));
    vector<vector<int>> parent(states, vector<int>(n, -1));

    // Start at city 0
    dp[1][0] = 0.0;

    for (int mask = 1; mask < states; mask++) {
        // Skip if city 0 not in mask
        if (!(mask & 1)) continue;

        for (int u = 0; u < n; u++) {
            // u must be in the current mask
            if (!(mask & (1 << u))) continue;
            if (dp[mask][u] == INF) continue;

            // Try going to each unvisited city v
            for (int v = 0; v < n; v++) {
                if (mask & (1 << v)) continue;  // already visited
                if (dist[u][v] == INF) continue; // no edge

                int newMask = mask | (1 << v);
                double newCost = dp[mask][u] + dist[u][v];

                if (newCost < dp[newMask][v]) {
                    dp[newMask][v] = newCost;
                    parent[newMask][v] = u;
                }
            }
        }
    }

    // Find optimal last city before returning to 0
    int fullMask = states - 1;
    double bestCost = INF;
    int lastCity = -1;

    for (int u = 1; u < n; u++) {
        if (dp[fullMask][u] == INF) continue;
        if (dist[u][0] == INF) continue;
        double total = dp[fullMask][u] + dist[u][0];
        if (total < bestCost) {
            bestCost = total;
            lastCity = u;
        }
    }

    // Reconstruct path
    vector<int> path;
    if (lastCity == -1) {
        // No valid tour found
        return {INF, {}};
    }

    // Reconstruct visited order (excluding return to start)
    int mask = fullMask;
    int cur = lastCity;
    while (cur != -1) {
        path.push_back(cur);
        int prev = parent[mask][cur];
        mask = mask ^ (1 << cur);
        cur = prev;
    }
    reverse(path.begin(), path.end());
    path.push_back(0); // return to depot

    return {bestCost, path};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    vector<vector<double>> dist(n, vector<double>(n));
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            cin >> dist[i][j];

    if (n == 1) {
        cout << fixed << setprecision(2) << 0.0 << "\n";
        cout << 0 << "\n";
        return 0;
    }

    Result res = heldKarp(dist, n);

    if (res.cost == INF) {
        cout << "NO_ROUTE\n";
        return 1;
    }

    cout << fixed << setprecision(2) << res.cost << "\n";
    for (int i = 0; i < (int)res.path.size(); i++) {
        if (i > 0) cout << " ";
        cout << res.path[i];
    }
    cout << "\n";

    return 0;
}
