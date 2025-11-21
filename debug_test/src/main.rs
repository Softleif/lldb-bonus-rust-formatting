use smallvec::SmallVec;
use smol_str::SmolStr;

#[inline(never)]
fn inspect_variables(
    some_f32: &Option<f32>,
    none_f32: &Option<f32>,
    some_i32: &Option<i32>,
    none_i32: &Option<i32>,
    some_string: &Option<String>,
    none_string: &Option<String>,
    some_bool: &Option<bool>,
    none_bool: &Option<bool>,
) {
    // Dummy function to set breakpoint on
    std::hint::black_box((
        some_f32,
        none_f32,
        some_i32,
        none_i32,
        some_string,
        none_string,
        some_bool,
        none_bool,
    ));
}

fn main() {
    // Inline variant - small strings (≤23 bytes typically)
    let inline_empty = SmolStr::new("");
    let inline_short = SmolStr::new("hello");
    let inline_medium = SmolStr::new("hello world!");

    // Static variant - using new_static
    const STATIC_STR: &str = "static string";
    let static_str = SmolStr::new_static(STATIC_STR);

    // Heap variant - large strings (>23 bytes)
    let heap_long = SmolStr::new("this is a very long string that will be heap allocated");
    let heap_repeated = SmolStr::new(&"x".repeat(100));

    // Additional test cases
    let inline_inline = SmolStr::new_inline("inline");
    let from_string = SmolStr::from(String::from("from string"));

    // SmallVec variants
    let inline_smallvec: SmallVec<u64, 2> = SmallVec::from([1, 2]);
    let heap_smallvec: SmallVec<u64, 2> = SmallVec::from([1, 2, 4, 5]);
    let empty_smallvec: SmallVec<u32, 4> = SmallVec::new();
    let single_smallvec: SmallVec<i32, 3> = SmallVec::from([42]);

    // Regular Vec for comparison
    let test_vec: Vec<u64> = vec![10, 20, 30];

    // Option variants
    let some_f32: Option<f32> = Some(1.3);
    let none_f32: Option<f32> = None;
    let some_i32: Option<i32> = Some(42);
    let none_i32: Option<i32> = None;
    let some_string: Option<String> = Some(String::from("hello"));
    let none_string: Option<String> = None;
    let some_bool: Option<bool> = Some(true);
    let none_bool: Option<bool> = None;

    // Prevent optimization of Option variables
    std::hint::black_box(&some_f32);
    std::hint::black_box(&none_f32);
    std::hint::black_box(&some_i32);
    std::hint::black_box(&none_i32);
    std::hint::black_box(&some_string);
    std::hint::black_box(&none_string);
    std::hint::black_box(&some_bool);
    std::hint::black_box(&none_bool);

    // Set breakpoint here - we can inspect all variants
    inspect_variables(
        &some_f32,
        &none_f32,
        &some_i32,
        &none_i32,
        &some_string,
        &none_string,
        &some_bool,
        &none_bool,
    );
    println!("inline_empty: {}", inline_empty);
    println!("inline_short: {}", inline_short);
    println!("inline_medium: {}", inline_medium);
    println!("static_str: {}", static_str);
    println!("heap_long: {}", heap_long);
    println!("heap_repeated: {}", heap_repeated);
    println!("inline_inline: {}", inline_inline);
    println!("from_string: {}", from_string);
    println!("inline_smallvec: {:?}", inline_smallvec);
    println!("heap_smallvec: {:?}", heap_smallvec);
    println!("empty_smallvec: {:?}", empty_smallvec);
    println!("single_smallvec: {:?}", single_smallvec);
    println!("test_vec: {:?}", test_vec);
    println!("some_f32: {:?}", some_f32);
    println!("none_f32: {:?}", none_f32);
    println!("some_i32: {:?}", some_i32);
    println!("none_i32: {:?}", none_i32);
    println!("some_string: {:?}", some_string);
    println!("none_string: {:?}", none_string);
    println!("some_bool: {:?}", some_bool);
    println!("none_bool: {:?}", none_bool);

    // Keep variables alive for debugging
    let _all = vec![
        inline_empty,
        inline_short,
        inline_medium,
        static_str,
        heap_long,
        heap_repeated,
        inline_inline,
        from_string,
    ];

    let _smallvecs = vec![
        inline_smallvec.len(),
        heap_smallvec.len(),
        empty_smallvec.len(),
        single_smallvec.len(),
        test_vec.len(),
    ];

    let _options = (
        &some_f32,
        &none_f32,
        &some_i32,
        &none_i32,
        &some_string,
        &none_string,
        &some_bool,
        &none_bool,
    );
}
