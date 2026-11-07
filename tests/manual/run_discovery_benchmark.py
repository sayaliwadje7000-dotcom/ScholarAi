import asyncio

from app.services.educational_resources.discovery_benchmark import (
    DiscoveryBenchmark,
)


async def simulated_discovery():
    await asyncio.sleep(0.02)

    return {
        "status": "success",
        "resources": [],
    }


async def main():
    result = await DiscoveryBenchmark.run(
        operation=simulated_discovery,
        iterations=20,
        warmup_iterations=3,
    )

    print("\nRESOURCE DISCOVERY BENCHMARK")
    print("-" * 40)

    for key, value in result.to_dict().items():
        print(f"{key}: {value}")

    print("-" * 40)


if __name__ == "__main__":
    asyncio.run(main())