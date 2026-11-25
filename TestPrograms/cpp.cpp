#include <cstdio>
#include <numeric>
#include <vector>

int main() {
    std::vector<int> values{10, 20, 12};
    const int sum = std::accumulate(values.begin(), values.end(), 0);
    std::printf("C++11 vector sum=%d\n", sum);
    return sum == 42 ? 0 : 1;
}
