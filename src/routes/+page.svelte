<script lang="ts">
    import {
        Grid,
        Row,
        Column,
        Slider,
        Tile,
        Toggle,
        InlineNotification,
        Button,
        Tabs, Tab, TabContent
    } from "carbon-components-svelte";
    import { onMount } from "svelte";

    let esc1 = 1000;
    let esc2 = 1000;
    let armed = false;
    let error = "";
    let armingTimeout: NodeJS.Timeout | null = null;
    let esc1Timeout: number | undefined, esc2Timeout: number | undefined;
    let isClient = false;

    onMount(() => {
        isClient = true;
    });

    const sendThrottle = async (esc: number, value: number) => {
        if (!isClient) return;
        try {
            const res = await fetch(
                `http://localhost:8000/set_throttle/?esc=${esc}&value=${value}`,
                {
                    method: "POST",
                },
            );
            if (!res.ok) throw new Error(`ESC ${esc} failed: ${res.status}`);
        } catch (e) {
            error = e.message;
        }
    };

    const armMotors = async () => {
        await sendThrottle(1, 1000);
        await sendThrottle(2, 1000);
        if (armingTimeout) clearTimeout(armingTimeout);
        armingTimeout = setTimeout(() => {
            sendThrottle(1, esc1);
            sendThrottle(2, esc2);
            armingTimeout = null;
        }, 2000);
    };


    // ✅ Reactive logic — now safe because it's guarded by `isClient`
    $: if (isClient && armed) {
        armMotors();
    } else if (isClient && !armed) {
        sendThrottle(1, 0);
        sendThrottle(2, 0);
    }

    $: if (isClient && armed && !armingTimeout) {
        clearTimeout(esc1Timeout);
        clearTimeout(esc2Timeout);

        esc1Timeout = setTimeout(() => sendThrottle(1, esc1), 100);
        esc2Timeout = setTimeout(() => sendThrottle(2, esc2), 100);
    }
</script>
<div id="statusBar">
    <InlineNotification kind="info" title="System Status" hideCloseButton subtitle={`Armed: ${armed}, ESC1: ${esc1}, ESC2: ${esc2}`} />
</div>
<Grid fullWidth>
    <Row>
        <Column>
            <h1 style="margin-top: 1rem;">
                Pickleball Machine - Motor Control
                
            </h1>
        </Column>
    </Row>

    <Row>
        <Column>
            <Toggle
                bind:toggled={armed}
                labelText="System Armed"
                id="arming-toggle"
                labelA="Disarmed"
                labelB="Armed"
            />
        </Column>
    </Row>

    {#if error}
        <Row> <Column sm="4" md="8" lg="16">
                <InlineNotification title="Throttle Error" subtitle={error} kind="error" lowContrast on:close={() => (error = "")} />
        </Column> </Row>
    {/if}

    <Row>
        <Column>
            <Tile>
                <h2>Upper Motor (ESC1)</h2>
                <Slider
                    bind:value={esc1}
                    min={1000}
                    max={2000}
                    step={10}
                    labelText="ESC 1 Throttle"
                    hideTextInput={false}
                />
                <p>MOT1 PWM: {esc1}µs</p>
            </Tile>
            <div class="motSpacer"></div>
            <Tile>
                <h2>Lower Motor (ESC2)</h2>
                <Slider
                    bind:value={esc2}
                    min={1000}
                    max={2000}
                    step={10}
                    labelText="ESC 2 Throttle"
                    hideTextInput={false}
                />
                <p>MOT2 PWM: {esc2}µs</p>
            </Tile>
        </Column>
        <Column>
            <Tile>
                <Button>Primary button</Button>
            </Tile>
        </Column>
    </Row>
    <Row>

    </Row>
</Grid>

<style>
#statusBar {
    margin: 0 auto;
    width: 50%;
}
.motSpacer{
    height: 2rem;
}
</style>
